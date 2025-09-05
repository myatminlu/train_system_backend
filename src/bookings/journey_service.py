from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from decimal import Decimal
import uuid

from src.routes.service import RouteService
from src.routes.schemas import RouteRequest
from src.schedules.service import ScheduleCalculationService
from src.schedules.realtime_service import realtime_simulator
from src.bookings.schemas import (
    PlannedJourney, JourneySegment, BookingValidation, PassengerInfo
)

class JourneyPlanningService:
    """Service for planning and validating journeys for booking"""
    
    def __init__(self, db: Session):
        self.db = db
        self.route_service = RouteService(db)
        self.schedule_service = ScheduleCalculationService(db)
        self._journey_cache = {}
    
    def plan_journey(
        self, 
        from_station_id: int,
        to_station_id: int,
        departure_time: datetime,
        passenger_count: int = 1,
        optimization: str = "time",
        max_transfers: int = 3
    ) -> Optional[PlannedJourney]:
        """Plan a complete journey for booking"""
        
        # Create route request
        route_request = RouteRequest(
            from_station_id=from_station_id,
            to_station_id=to_station_id,
            departure_time=departure_time,
            passenger_type_id=1,  # Default to adult
            optimization=optimization,
            max_walking_time=15,
            max_transfers=max_transfers
        )
        
        # Get route options
        routes = self.route_service.plan_route(route_request)
        
        if not routes:
            return None
        
        # Use the best route (first in list)
        best_route = routes[0]
        
        # Convert route to planned journey
        journey = self._convert_route_to_journey(best_route, passenger_count, optimization)
        
        # Cache the journey for booking
        self._journey_cache[journey.journey_id] = journey
        
        return journey
    
    def get_journey_by_id(self, journey_id: str) -> Optional[PlannedJourney]:
        """Retrieve a planned journey by ID"""
        return self._journey_cache.get(journey_id)
    
    def validate_journey_for_booking(
        self, 
        journey_id: str,
        passengers: List[PassengerInfo],
        booking_time: datetime = None
    ) -> BookingValidation:
        """Validate if a journey can be booked"""
        
        if not booking_time:
            booking_time = datetime.now()
        
        errors = []
        warnings = []
        
        # Check if journey exists
        journey = self.get_journey_by_id(journey_id)
        if not journey:
            return BookingValidation(
                is_valid=False,
                errors=["Journey not found or expired"],
                journey_available=False
            )
        
        # Check if journey is still valid (not too old)
        journey_age = (booking_time - journey.created_at).total_seconds() / 60
        if journey_age > 30:  # 30 minutes validity
            errors.append("Journey plan has expired. Please search again.")
            return BookingValidation(
                is_valid=False,
                errors=errors,
                journey_available=False
            )
        
        # Check if departure time is still in future
        if journey.departure_time <= booking_time:
            errors.append("Departure time has passed")
        
        # Check if departure is not too far in future (max 30 days)
        if journey.departure_time > booking_time + timedelta(days=30):
            errors.append("Cannot book journeys more than 30 days in advance")
        
        # Validate passenger count
        if len(passengers) > 10:
            errors.append("Maximum 10 passengers per booking")
        elif len(passengers) == 0:
            errors.append("At least 1 passenger required")
        
        # Check service availability
        capacity_available = self._check_capacity_availability(journey, len(passengers))
        if not capacity_available:
            warnings.append("High demand expected for this journey. Book early to secure seats.")
        
        # Check for service disruptions
        schedule_conflicts = self._check_service_disruptions(journey, booking_time)
        if schedule_conflicts:
            warnings.extend(schedule_conflicts)
        
        # Calculate total cost with current passenger mix
        estimated_cost = self._calculate_total_cost(journey, passengers)
        
        is_valid = len(errors) == 0
        
        return BookingValidation(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            journey_available=True,
            capacity_available=capacity_available,
            schedule_conflicts=schedule_conflicts,
            estimated_total_cost=estimated_cost
        )
    
    def refresh_journey_timing(self, journey_id: str) -> Optional[PlannedJourney]:
        """Refresh journey with latest timing information"""
        
        journey = self.get_journey_by_id(journey_id)
        if not journey:
            return None
        
        # Get updated departure predictions for each segment
        updated_segments = []
        current_time = journey.departure_time
        
        for segment in journey.segments:
            if segment.transport_type == "train":
                # Get latest predictions for this station
                departures = self.schedule_service.calculate_departures_for_station(
                    segment.from_station_id,
                    hours_ahead=1
                )
                
                # Find the closest departure to our planned time
                closest_departure = None
                min_diff = timedelta.max
                
                for dep in departures:
                    if dep.line_id == segment.line_id:
                        diff = abs(dep.predicted_time - segment.departure_time)
                        if diff < min_diff:
                            min_diff = diff
                            closest_departure = dep
                
                if closest_departure:
                    # Update segment timing
                    delay_adjustment = closest_departure.predicted_time - segment.departure_time
                    segment.departure_time = closest_departure.predicted_time
                    segment.arrival_time += delay_adjustment
                    current_time = segment.arrival_time
            
            updated_segments.append(segment)
        
        # Update journey timing
        journey.segments = updated_segments
        journey.departure_time = updated_segments[0].departure_time
        journey.arrival_time = updated_segments[-1].arrival_time
        journey.total_duration_minutes = int(
            (journey.arrival_time - journey.departure_time).total_seconds() / 60
        )
        
        # Update cache
        self._journey_cache[journey_id] = journey
        
        return journey
    
    def get_alternative_journeys(
        self,
        original_journey_id: str,
        max_alternatives: int = 3
    ) -> List[PlannedJourney]:
        """Get alternative journey options"""
        
        original = self.get_journey_by_id(original_journey_id)
        if not original:
            return []
        
        alternatives = []
        
        # Try different departure times (earlier and later)
        time_offsets = [-30, -15, 15, 30, 60]  # Minutes
        
        for offset in time_offsets:
            if len(alternatives) >= max_alternatives:
                break
            
            new_departure = original.departure_time + timedelta(minutes=offset)
            
            # Skip if too close to original
            if abs(offset) < 10:
                continue
            
            alt_journey = self.plan_journey(
                from_station_id=original.from_station_id,
                to_station_id=original.to_station_id,
                departure_time=new_departure,
                optimization=original.optimization_used
            )
            
            if alt_journey and alt_journey.journey_id != original.journey_id:
                alternatives.append(alt_journey)
        
        return alternatives
    
    def _convert_route_to_journey(
        self, 
        route, 
        passenger_count: int,
        optimization: str
    ) -> PlannedJourney:
        """Convert RouteOption to PlannedJourney"""
        
        journey_id = str(uuid.uuid4())
        
        # Convert route segments to journey segments
        journey_segments = []
        for segment in route.segments:
            journey_segment = JourneySegment(
                segment_order=segment.segment_order,
                from_station_id=segment.from_station_id,
                from_station_name=segment.from_station_name,
                to_station_id=segment.to_station_id,
                to_station_name=segment.to_station_name,
                line_id=segment.line_id or 0,
                line_name=segment.line_name or "Transfer",
                transport_type=segment.transport_type,
                departure_time=segment.departure_time or datetime.now(),
                arrival_time=segment.arrival_time or datetime.now(),
                duration_minutes=segment.duration_minutes,
                cost=segment.cost * passenger_count,  # Multiply by passenger count
                platform_info=segment.platform_info,
                instructions=segment.instructions
            )
            journey_segments.append(journey_segment)
        
        # Create planned journey
        journey = PlannedJourney(
            journey_id=journey_id,
            from_station_id=route.segments[0].from_station_id,
            to_station_id=route.segments[-1].to_station_id,
            departure_time=route.summary.departure_time,
            arrival_time=route.summary.arrival_time,
            total_duration_minutes=route.summary.total_duration_minutes,
            total_cost=route.summary.total_cost * passenger_count,
            total_transfers=route.summary.total_transfers,
            segments=journey_segments,
            optimization_used=optimization
        )
        
        return journey
    
    def _check_capacity_availability(self, journey: PlannedJourney, passenger_count: int) -> bool:
        """Check if capacity is available for the journey"""
        
        # Simplified capacity check - in real system would check actual train capacity
        # Check for high-demand times
        departure_hour = journey.departure_time.hour
        
        # Rush hour capacity constraints
        if departure_hour in [7, 8, 17, 18, 19]:
            # Higher chance of capacity issues during rush hour
            if passenger_count > 6:
                return False
            
            # Check for service alerts that might reduce capacity
            active_alerts = realtime_simulator.get_service_alerts(active_only=True)
            for alert in active_alerts:
                if any(segment.line_id in alert.affected_lines for segment in journey.segments):
                    if passenger_count > 4:
                        return False
        
        return True
    
    def _check_service_disruptions(
        self, 
        journey: PlannedJourney,
        booking_time: datetime
    ) -> List[str]:
        """Check for service disruptions affecting the journey"""
        
        conflicts = []
        
        # Get active service alerts
        active_alerts = realtime_simulator.get_service_alerts(active_only=True)
        
        for alert in active_alerts:
            # Check if alert affects any segment of the journey
            for segment in journey.segments:
                if segment.line_id in alert.affected_lines:
                    conflict_msg = f"{alert.title}: {alert.description}"
                    if conflict_msg not in conflicts:
                        conflicts.append(conflict_msg)
                
                if (segment.from_station_id in alert.affected_stations or 
                    segment.to_station_id in alert.affected_stations):
                    conflict_msg = f"Station service alert: {alert.title}"
                    if conflict_msg not in conflicts:
                        conflicts.append(conflict_msg)
        
        # Check for maintenance windows
        maintenance_windows = realtime_simulator.get_maintenance_windows(active_only=True)
        
        for maintenance in maintenance_windows:
            # Check if maintenance affects journey time
            if (maintenance.start_time <= journey.arrival_time and 
                maintenance.end_time >= journey.departure_time):
                
                for segment in journey.segments:
                    if segment.line_id in maintenance.affected_lines:
                        conflicts.append(
                            f"Scheduled maintenance: {maintenance.title} "
                            f"({maintenance.start_time.strftime('%H:%M')} - "
                            f"{maintenance.end_time.strftime('%H:%M')})"
                        )
                        break
        
        return conflicts
    
    def _calculate_total_cost(
        self, 
        journey: PlannedJourney,
        passengers: List[PassengerInfo]
    ) -> Decimal:
        """Calculate total cost with passenger-specific pricing"""
        
        from src.routes.fare_service import FareCalculationService
        
        fare_service = FareCalculationService(self.db)
        total_cost = Decimal('0')
        
        # Calculate cost per passenger type
        passenger_type_counts = {}
        for passenger in passengers:
            pt_id = passenger.passenger_type_id
            passenger_type_counts[pt_id] = passenger_type_counts.get(pt_id, 0) + 1
        
        # Base cost from journey
        base_cost_per_person = journey.total_cost / len(passengers) if passengers else journey.total_cost
        
        for passenger_type_id, count in passenger_type_counts.items():
            # Get discount for passenger type
            discount_info = fare_service.get_discount_info(passenger_type_id)
            discount_percentage = discount_info.get('discount_percentage', Decimal('0'))
            
            # Calculate cost with discount
            passenger_cost = base_cost_per_person * (Decimal('100') - discount_percentage) / Decimal('100')
            total_cost += passenger_cost * count
        
        return total_cost
    
    def cleanup_expired_journeys(self, max_age_minutes: int = 60):
        """Clean up expired journey plans from cache"""
        
        current_time = datetime.now()
        expired_ids = []
        
        for journey_id, journey in self._journey_cache.items():
            age_minutes = (current_time - journey.created_at).total_seconds() / 60
            if age_minutes > max_age_minutes:
                expired_ids.append(journey_id)
        
        for journey_id in expired_ids:
            del self._journey_cache[journey_id]
        
        return len(expired_ids)