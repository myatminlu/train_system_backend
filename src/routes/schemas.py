from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime, time
from decimal import Decimal

class RouteRequest(BaseModel):
    """Request schema for route planning"""
    from_station_id: int
    to_station_id: int
    departure_time: Optional[datetime] = None
    passenger_type_id: int = 1  # Default to adult
    optimization: Literal["time", "cost", "transfers"] = "time"
    max_walking_time: int = 10  # Maximum walking time for transfers in minutes
    max_transfers: int = 3  # Maximum number of transfers allowed

class RouteSegment(BaseModel):
    """Individual segment of a route"""
    segment_order: int
    transport_type: Literal["train", "walk", "transfer"]
    from_station_id: int
    from_station_name: str
    to_station_id: int
    to_station_name: str
    line_id: Optional[int] = None
    line_name: Optional[str] = None
    line_color: Optional[str] = None
    duration_minutes: int
    distance_km: Optional[Decimal] = None
    cost: Decimal
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    instructions: str  # Human-readable instructions
    platform_info: Optional[str] = None

class RouteSummary(BaseModel):
    """Summary information for a complete route"""
    total_duration_minutes: int
    total_cost: Decimal
    total_distance_km: Optional[Decimal] = None
    total_transfers: int
    total_walking_time_minutes: int
    departure_time: datetime
    arrival_time: datetime
    lines_used: List[str]  # Names of lines used

class RouteOption(BaseModel):
    """Complete route option with all segments"""
    route_id: str  # Unique identifier for this route
    segments: List[RouteSegment]
    summary: RouteSummary
    optimization_score: float  # Score based on optimization preference
    carbon_footprint_kg: Optional[Decimal] = None

class RouteResponse(BaseModel):
    """Response schema for route planning"""
    request: RouteRequest
    routes: List[RouteOption]
    total_options: int
    calculation_time_ms: int

class FareCalculationRequest(BaseModel):
    """Request schema for fare calculation"""
    route_segments: List[dict]  # Route segments for fare calculation
    passenger_type_id: int = 1

class FareBreakdown(BaseModel):
    """Detailed fare breakdown"""
    segment_id: int
    segment_type: Literal["train", "transfer"]
    line_name: Optional[str] = None
    base_fare: Decimal
    distance_fare: Decimal
    transfer_fee: Decimal
    passenger_discount: Decimal
    segment_total: Decimal

class FareCalculationResponse(BaseModel):
    """Response schema for fare calculation"""
    total_fare: Decimal
    passenger_type: str
    discount_percentage: Decimal
    breakdown: List[FareBreakdown]
    currency: str = "THB"

class RouteValidationError(BaseModel):
    """Route validation error details"""
    error_code: str
    error_message: str
    field: Optional[str] = None

class NetworkNode(BaseModel):
    """Network graph node representation"""
    station_id: int
    station_name: str
    line_id: Optional[int] = None
    line_name: Optional[str] = None
    lat: Optional[Decimal] = None
    long: Optional[Decimal] = None
    is_interchange: bool = False

class NetworkEdge(BaseModel):
    """Network graph edge representation"""
    from_station_id: int
    to_station_id: int
    transport_type: Literal["train", "walk", "transfer"]
    duration_minutes: int
    cost: Decimal
    distance_km: Optional[Decimal] = None
    line_id: Optional[int] = None
    transfer_time_minutes: Optional[int] = None

class RouteAlternativesRequest(BaseModel):
    """Request for alternative routes"""
    from_station_id: int
    to_station_id: int
    departure_time: Optional[datetime] = None
    passenger_type_id: int = 1
    max_alternatives: int = 5
    avoid_lines: Optional[List[int]] = None  # Line IDs to avoid
    prefer_lines: Optional[List[int]] = None  # Preferred line IDs