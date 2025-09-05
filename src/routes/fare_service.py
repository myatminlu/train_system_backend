from typing import List, Dict, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from src.models import FareRule, PassengerType, TrainLine, Station, TransferPoint
from src.routes.schemas import (
    RouteOption, RouteSegment, FareCalculationRequest, FareCalculationResponse, 
    FareBreakdown
)
import math

class FareCalculationService:
    """Service for calculating fares across different train systems"""
    
    def __init__(self, db: Session):
        self.db = db
        self._fare_rules_cache = {}
        self._passenger_types_cache = {}
        self._load_fare_rules()
        self._load_passenger_types()
    
    def _load_fare_rules(self):
        """Load and cache fare rules for all routes"""
        rules = self.db.query(FareRule).all()
        for rule in rules:
            self._fare_rules_cache[rule.route_id] = rule
    
    def _load_passenger_types(self):
        """Load and cache passenger types for discount calculations"""
        types = self.db.query(PassengerType).all()
        for ptype in types:
            self._passenger_types_cache[ptype.id] = ptype
    
    def calculate_route_fare(
        self, 
        route: RouteOption, 
        passenger_type_id: int = 1
    ) -> FareCalculationResponse:
        """Calculate total fare for a complete route"""
        breakdown = []
        total_fare = Decimal('0')
        
        passenger_type = self._passenger_types_cache.get(passenger_type_id)
        discount_percentage = passenger_type.discount_percentage if passenger_type else Decimal('0')
        
        segment_id = 1
        for segment in route.segments:
            if segment.transport_type in ["train", "transfer"]:
                fare_detail = self._calculate_segment_fare(
                    segment, passenger_type_id, segment_id
                )
                breakdown.append(fare_detail)
                total_fare += fare_detail.segment_total
                segment_id += 1
        
        return FareCalculationResponse(
            total_fare=total_fare,
            passenger_type=passenger_type.type_name if passenger_type else "Adult",
            discount_percentage=discount_percentage,
            breakdown=breakdown,
            currency="THB"
        )
    
    def _calculate_segment_fare(
        self, 
        segment: RouteSegment, 
        passenger_type_id: int,
        segment_id: int
    ) -> FareBreakdown:
        """Calculate fare for a single route segment"""
        
        if segment.transport_type == "train":
            return self._calculate_train_fare(segment, passenger_type_id, segment_id)
        elif segment.transport_type == "transfer":
            return self._calculate_transfer_fare(segment, passenger_type_id, segment_id)
        else:
            # Walking segments are free
            return FareBreakdown(
                segment_id=segment_id,
                segment_type=segment.transport_type,
                line_name=segment.line_name,
                base_fare=Decimal('0'),
                distance_fare=Decimal('0'),
                transfer_fee=Decimal('0'),
                passenger_discount=Decimal('0'),
                segment_total=Decimal('0')
            )
    
    def _calculate_train_fare(
        self, 
        segment: RouteSegment, 
        passenger_type_id: int,
        segment_id: int
    ) -> FareBreakdown:
        """Calculate fare for train segment based on line's fare structure"""
        
        fare_rule = self._fare_rules_cache.get(segment.line_id)
        if not fare_rule:
            # Default fare if no rule found
            base_fare = Decimal('25.00')
            distance_fare = Decimal('0')
        else:
            base_fare = fare_rule.base_fare
            distance_fare = self._calculate_distance_fare(segment, fare_rule)
        
        # Get passenger discount
        passenger_type = self._passenger_types_cache.get(passenger_type_id)
        discount_percentage = passenger_type.discount_percentage if passenger_type else Decimal('0')
        
        # Calculate discount amount
        subtotal = base_fare + distance_fare
        discount_amount = subtotal * (discount_percentage / Decimal('100'))
        segment_total = subtotal - discount_amount
        
        return FareBreakdown(
            segment_id=segment_id,
            segment_type="train",
            line_name=segment.line_name,
            base_fare=base_fare,
            distance_fare=distance_fare,
            transfer_fee=Decimal('0'),
            passenger_discount=discount_amount,
            segment_total=segment_total
        )
    
    def _calculate_distance_fare(
        self, 
        segment: RouteSegment, 
        fare_rule: FareRule
    ) -> Decimal:
        """Calculate distance-based fare component"""
        
        if fare_rule.fare_type == "zone_based":
            # Zone-based fare (MRT style)
            return self._calculate_zone_fare(segment, fare_rule)
        elif fare_rule.fare_type == "distance_based":
            # Distance-based fare (BTS style)
            return self._calculate_distance_based_fare(segment, fare_rule)
        else:
            # Flat fare
            return Decimal('0')
    
    def _calculate_zone_fare(
        self, 
        segment: RouteSegment, 
        fare_rule: FareRule
    ) -> Decimal:
        """Calculate zone-based fare (MRT system)"""
        
        # Get zone information for stations
        from_station = self.db.query(Station).filter(
            Station.id == segment.from_station_id
        ).first()
        to_station = self.db.query(Station).filter(
            Station.id == segment.to_station_id
        ).first()
        
        if not from_station or not to_station:
            return Decimal('0')
        
        # Calculate zone difference
        zone_diff = abs((from_station.zone_number or 1) - (to_station.zone_number or 1))
        
        if zone_diff <= 1:
            return Decimal('0')  # Same zone or adjacent zones
        else:
            # Additional fare for each zone beyond first
            return fare_rule.per_zone_fare * Decimal(str(zone_diff - 1))
    
    def _calculate_distance_based_fare(
        self, 
        segment: RouteSegment, 
        fare_rule: FareRule
    ) -> Decimal:
        """Calculate distance-based fare (BTS system)"""
        
        if segment.distance_km:
            distance = segment.distance_km
        else:
            # Estimate distance from coordinates
            distance = self._estimate_segment_distance(segment)
        
        if distance <= fare_rule.distance_threshold_km:
            return Decimal('0')  # Within base distance
        else:
            # Additional fare for extra distance
            extra_distance = distance - fare_rule.distance_threshold_km
            return fare_rule.per_km_fare * extra_distance
    
    def _estimate_segment_distance(self, segment: RouteSegment) -> Decimal:
        """Estimate distance between stations using coordinates"""
        
        from_station = self.db.query(Station).filter(
            Station.id == segment.from_station_id
        ).first()
        to_station = self.db.query(Station).filter(
            Station.id == segment.to_station_id
        ).first()
        
        if not from_station or not to_station or not all([
            from_station.lat, from_station.long, to_station.lat, to_station.long
        ]):
            return Decimal('2.0')  # Default distance
        
        # Haversine formula for distance calculation
        lat1, lon1 = float(from_station.lat), float(from_station.long)
        lat2, lon2 = float(to_station.lat), float(to_station.long)
        
        R = 6371  # Earth's radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return Decimal(str(round(distance, 2)))
    
    def _calculate_transfer_fare(
        self, 
        segment: RouteSegment, 
        passenger_type_id: int,
        segment_id: int
    ) -> FareBreakdown:
        """Calculate fare for transfer segment"""
        
        # Get transfer fee from database
        transfer = self.db.query(TransferPoint).filter(
            TransferPoint.station_a_id == segment.from_station_id,
            TransferPoint.station_b_id == segment.to_station_id
        ).first()
        
        if not transfer:
            # Try reverse direction
            transfer = self.db.query(TransferPoint).filter(
                TransferPoint.station_a_id == segment.to_station_id,
                TransferPoint.station_b_id == segment.from_station_id
            ).first()
        
        transfer_fee = transfer.transfer_fee if transfer else Decimal('0')
        
        # Apply passenger discount
        passenger_type = self._passenger_types_cache.get(passenger_type_id)
        discount_percentage = passenger_type.discount_percentage if passenger_type else Decimal('0')
        
        discount_amount = transfer_fee * (discount_percentage / Decimal('100'))
        segment_total = transfer_fee - discount_amount
        
        return FareBreakdown(
            segment_id=segment_id,
            segment_type="transfer",
            line_name=None,
            base_fare=Decimal('0'),
            distance_fare=Decimal('0'),
            transfer_fee=transfer_fee,
            passenger_discount=discount_amount,
            segment_total=segment_total
        )
    
    def calculate_fare_from_request(
        self, 
        request: FareCalculationRequest
    ) -> FareCalculationResponse:
        """Calculate fare from fare calculation request"""
        
        breakdown = []
        total_fare = Decimal('0')
        
        passenger_type = self._passenger_types_cache.get(request.passenger_type_id)
        discount_percentage = passenger_type.discount_percentage if passenger_type else Decimal('0')
        
        for i, segment_data in enumerate(request.route_segments):
            # Convert dict to RouteSegment for fare calculation
            segment = RouteSegment(
                segment_order=i + 1,
                transport_type=segment_data.get("transport_type", "train"),
                from_station_id=segment_data["from_station_id"],
                from_station_name=segment_data.get("from_station_name", ""),
                to_station_id=segment_data["to_station_id"],
                to_station_name=segment_data.get("to_station_name", ""),
                line_id=segment_data.get("line_id"),
                line_name=segment_data.get("line_name"),
                duration_minutes=segment_data.get("duration_minutes", 0),
                distance_km=Decimal(str(segment_data["distance_km"])) if segment_data.get("distance_km") else None,
                cost=Decimal(str(segment_data.get("cost", 0))),
                instructions=""
            )
            
            fare_detail = self._calculate_segment_fare(segment, request.passenger_type_id, i + 1)
            breakdown.append(fare_detail)
            total_fare += fare_detail.segment_total
        
        return FareCalculationResponse(
            total_fare=total_fare,
            passenger_type=passenger_type.type_name if passenger_type else "Adult",
            discount_percentage=discount_percentage,
            breakdown=breakdown,
            currency="THB"
        )
    
    def compare_route_fares(
        self, 
        routes: List[RouteOption], 
        passenger_type_id: int = 1
    ) -> List[Dict]:
        """Compare fares across multiple route options"""
        
        comparisons = []
        
        for i, route in enumerate(routes):
            fare_response = self.calculate_route_fare(route, passenger_type_id)
            
            comparison = {
                "route_index": i,
                "route_id": route.route_id,
                "total_fare": fare_response.total_fare,
                "total_duration": route.summary.total_duration_minutes,
                "total_transfers": route.summary.total_transfers,
                "fare_per_minute": fare_response.total_fare / Decimal(str(route.summary.total_duration_minutes)),
                "lines_used": route.summary.lines_used,
                "breakdown": fare_response.breakdown
            }
            comparisons.append(comparison)
        
        # Sort by total fare (cheapest first)
        comparisons.sort(key=lambda x: x["total_fare"])
        
        return comparisons
    
    def get_discount_info(self, passenger_type_id: int) -> Dict:
        """Get discount information for a passenger type"""
        
        passenger_type = self._passenger_types_cache.get(passenger_type_id)
        if not passenger_type:
            return {
                "passenger_type": "Adult",
                "discount_percentage": Decimal('0'),
                "description": "No discount available"
            }
        
        return {
            "passenger_type": passenger_type.type_name,
            "discount_percentage": passenger_type.discount_percentage,
            "description": passenger_type.description,
            "age_requirement": getattr(passenger_type, 'age_requirement', None)
        }