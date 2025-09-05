from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models import Station, TrainLine, PassengerType
from src.routes.schemas import RouteRequest, RouteAlternativesRequest, RouteValidationError

class RouteValidator:
    """Service for validating route planning requests"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_route_request(self, request: RouteRequest) -> List[RouteValidationError]:
        """Validate a route planning request"""
        errors = []
        
        # Basic validation
        if request.from_station_id == request.to_station_id:
            errors.append(RouteValidationError(
                error_code="SAME_STATION",
                error_message="Origin and destination stations cannot be the same",
                field="to_station_id"
            ))
        
        # Validate stations exist
        from_station = self.db.query(Station).filter(
            Station.id == request.from_station_id
        ).first()
        if not from_station:
            errors.append(RouteValidationError(
                error_code="INVALID_FROM_STATION",
                error_message=f"Origin station with ID {request.from_station_id} not found",
                field="from_station_id"
            ))
        elif from_station.status != "active":
            errors.append(RouteValidationError(
                error_code="STATION_INACTIVE",
                error_message=f"Origin station '{from_station.name}' is currently inactive",
                field="from_station_id"
            ))
        
        to_station = self.db.query(Station).filter(
            Station.id == request.to_station_id
        ).first()
        if not to_station:
            errors.append(RouteValidationError(
                error_code="INVALID_TO_STATION",
                error_message=f"Destination station with ID {request.to_station_id} not found",
                field="to_station_id"
            ))
        elif to_station.status != "active":
            errors.append(RouteValidationError(
                error_code="STATION_INACTIVE",
                error_message=f"Destination station '{to_station.name}' is currently inactive",
                field="to_station_id"
            ))
        
        # Validate passenger type
        passenger_type = self.db.query(PassengerType).filter(
            PassengerType.id == request.passenger_type_id
        ).first()
        if not passenger_type:
            errors.append(RouteValidationError(
                error_code="INVALID_PASSENGER_TYPE",
                error_message=f"Passenger type with ID {request.passenger_type_id} not found",
                field="passenger_type_id"
            ))
        
        # Validate departure time
        if request.departure_time:
            # Always use timezone-naive datetime for comparison
            if request.departure_time.tzinfo:
                departure_time = request.departure_time.replace(tzinfo=None)
            else:
                departure_time = request.departure_time
                
            current_time = datetime.now()
            
            if departure_time < current_time - timedelta(hours=1):
                errors.append(RouteValidationError(
                    error_code="PAST_DEPARTURE_TIME",
                    error_message="Departure time cannot be more than 1 hour in the past",
                    field="departure_time"
                ))
            
            # Check if departure time is too far in future (e.g., more than 30 days)
            max_future_time = current_time + timedelta(days=30)
            if departure_time > max_future_time:
                errors.append(RouteValidationError(
                    error_code="FUTURE_DEPARTURE_TIME",
                    error_message="Departure time cannot be more than 30 days in the future",
                    field="departure_time"
                ))
        
        # Validate constraints
        if request.max_walking_time < 1:
            errors.append(RouteValidationError(
                error_code="INVALID_WALKING_TIME",
                error_message="Maximum walking time must be at least 1 minute",
                field="max_walking_time"
            ))
        elif request.max_walking_time > 60:
            errors.append(RouteValidationError(
                error_code="EXCESSIVE_WALKING_TIME",
                error_message="Maximum walking time cannot exceed 60 minutes",
                field="max_walking_time"
            ))
        
        if request.max_transfers < 0:
            errors.append(RouteValidationError(
                error_code="INVALID_TRANSFERS",
                error_message="Maximum transfers cannot be negative",
                field="max_transfers"
            ))
        elif request.max_transfers > 5:
            errors.append(RouteValidationError(
                error_code="EXCESSIVE_TRANSFERS",
                error_message="Maximum transfers cannot exceed 5",
                field="max_transfers"
            ))
        
        # Validate optimization preference
        valid_optimizations = ["time", "cost", "transfers"]
        if request.optimization not in valid_optimizations:
            errors.append(RouteValidationError(
                error_code="INVALID_OPTIMIZATION",
                error_message=f"Optimization must be one of: {', '.join(valid_optimizations)}",
                field="optimization"
            ))
        
        return errors
    
    def validate_alternatives_request(
        self, 
        request: RouteAlternativesRequest
    ) -> List[RouteValidationError]:
        """Validate a route alternatives request"""
        errors = []
        
        # Basic validation similar to route request
        base_errors = self.validate_route_request(RouteRequest(
            from_station_id=request.from_station_id,
            to_station_id=request.to_station_id,
            departure_time=request.departure_time,
            passenger_type_id=request.passenger_type_id
        ))
        errors.extend(base_errors)
        
        # Additional validation for alternatives-specific fields
        if request.max_alternatives < 1:
            errors.append(RouteValidationError(
                error_code="INVALID_MAX_ALTERNATIVES",
                error_message="Maximum alternatives must be at least 1",
                field="max_alternatives"
            ))
        elif request.max_alternatives > 10:
            errors.append(RouteValidationError(
                error_code="EXCESSIVE_ALTERNATIVES",
                error_message="Maximum alternatives cannot exceed 10",
                field="max_alternatives"
            ))
        
        # Validate avoid_lines
        if request.avoid_lines:
            for line_id in request.avoid_lines:
                line = self.db.query(TrainLine).filter(TrainLine.id == line_id).first()
                if not line:
                    errors.append(RouteValidationError(
                        error_code="INVALID_AVOID_LINE",
                        error_message=f"Line ID {line_id} in avoid_lines not found",
                        field="avoid_lines"
                    ))
                elif line.status != "active":
                    errors.append(RouteValidationError(
                        error_code="INACTIVE_AVOID_LINE",
                        error_message=f"Line '{line.name}' in avoid_lines is inactive",
                        field="avoid_lines"
                    ))
        
        # Validate prefer_lines
        if request.prefer_lines:
            for line_id in request.prefer_lines:
                line = self.db.query(TrainLine).filter(TrainLine.id == line_id).first()
                if not line:
                    errors.append(RouteValidationError(
                        error_code="INVALID_PREFER_LINE",
                        error_message=f"Line ID {line_id} in prefer_lines not found",
                        field="prefer_lines"
                    ))
                elif line.status != "active":
                    errors.append(RouteValidationError(
                        error_code="INACTIVE_PREFER_LINE",
                        error_message=f"Line '{line.name}' in prefer_lines is inactive",
                        field="prefer_lines"
                    ))
        
        # Check for conflicts between avoid and prefer lines
        if request.avoid_lines and request.prefer_lines:
            common_lines = set(request.avoid_lines) & set(request.prefer_lines)
            if common_lines:
                errors.append(RouteValidationError(
                    error_code="CONFLICTING_LINE_PREFERENCES",
                    error_message=f"Lines {list(common_lines)} cannot be both avoided and preferred",
                    field="prefer_lines"
                ))
        
        return errors
    
    def validate_station_connectivity(
        self, 
        from_station_id: int, 
        to_station_id: int
    ) -> Tuple[bool, Optional[str]]:
        """Check if two stations are potentially connected"""
        
        from_station = self.db.query(Station).filter(
            Station.id == from_station_id
        ).first()
        to_station = self.db.query(Station).filter(
            Station.id == to_station_id
        ).first()
        
        if not from_station or not to_station:
            return False, "One or both stations not found"
        
        # Check if stations are on the same line (direct connection)
        if from_station.line_id == to_station.line_id:
            return True, None
        
        # Check if there's a potential path through interchange stations
        # This is a simplified check - the actual route calculation will determine feasibility
        from sqlalchemy import text
        
        # Query to check if there's any path through the network
        # This uses a simplified approach - checking if both stations are connected
        # to interchange stations that could provide a path
        query = text("""
            WITH station_networks AS (
                SELECT DISTINCT s1.id as station_id, s2.id as connected_station_id
                FROM stations s1
                JOIN stations s2 ON s1.line_id = s2.line_id
                WHERE s1.id != s2.id
                UNION
                SELECT tp.station_a_id, tp.station_b_id
                FROM transfer_points tp
                WHERE tp.is_active = true
                UNION
                SELECT tp.station_b_id, tp.station_a_id
                FROM transfer_points tp
                WHERE tp.is_active = true
            )
            SELECT COUNT(*) as path_count
            FROM station_networks sn1
            JOIN station_networks sn2 ON sn1.connected_station_id = sn2.station_id
            WHERE sn1.station_id = :from_id AND sn2.connected_station_id = :to_id
        """)
        
        result = self.db.execute(query, {
            "from_id": from_station_id, 
            "to_id": to_station_id
        }).scalar()
        
        if result and result > 0:
            return True, None
        else:
            return False, "No potential route found between stations"
    
    def check_service_disruptions(
        self, 
        line_ids: List[int], 
        departure_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Check for service disruptions that might affect routes"""
        
        # This would integrate with the service status system
        # For now, return empty list as placeholder
        disruptions = []
        
        # In a real system, you would query service disruptions:
        # - Planned maintenance
        # - Service interruptions
        # - Delays
        # - Line closures
        
        # Example structure:
        # disruptions.append({
        #     "line_id": line_id,
        #     "disruption_type": "maintenance",
        #     "description": "Scheduled maintenance on weekends",
        #     "start_time": datetime(...),
        #     "end_time": datetime(...),
        #     "severity": "moderate"
        # })
        
        return disruptions
    
    def validate_route_feasibility(
        self, 
        request: RouteRequest
    ) -> Tuple[bool, List[str]]:
        """Validate if a route request is feasible"""
        
        warnings = []
        
        # Check basic connectivity
        is_connected, connectivity_message = self.validate_station_connectivity(
            request.from_station_id, 
            request.to_station_id
        )
        
        if not is_connected:
            return False, [connectivity_message or "Stations are not connected"]
        
        # Check if constraints are too restrictive
        if request.max_transfers == 0:
            # Check if stations are on the same line
            from_station = self.db.query(Station).filter(
                Station.id == request.from_station_id
            ).first()
            to_station = self.db.query(Station).filter(
                Station.id == request.to_station_id
            ).first()
            
            if from_station and to_station and from_station.line_id != to_station.line_id:
                return False, ["No transfers allowed but stations are on different lines"]
        
        if request.max_walking_time < 5 and request.max_transfers > 0:
            warnings.append("Very low walking time limit may prevent finding routes with transfers")
        
        # Check service disruptions
        departure_time = request.departure_time or datetime.now()
        
        # Get all lines that might be used (simplified check)
        from_line_id = self.db.query(Station.line_id).filter(
            Station.id == request.from_station_id
        ).scalar()
        to_line_id = self.db.query(Station.line_id).filter(
            Station.id == request.to_station_id
        ).scalar()
        
        potential_lines = [line_id for line_id in [from_line_id, to_line_id] if line_id]
        disruptions = self.check_service_disruptions(potential_lines, departure_time)
        
        if disruptions:
            for disruption in disruptions:
                warnings.append(f"Service disruption on {disruption.get('line_name', 'line')}: {disruption.get('description', 'Unknown issue')}")
        
        return True, warnings