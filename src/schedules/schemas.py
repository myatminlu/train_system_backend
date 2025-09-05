from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any
from datetime import datetime, time
from decimal import Decimal
from enum import Enum

class ScheduleType(str, Enum):
    """Schedule type enumeration"""
    WEEKDAY = "weekday"
    WEEKEND = "weekend" 
    HOLIDAY = "holiday"
    SPECIAL_EVENT = "special_event"

class ServiceStatus(str, Enum):
    """Service status enumeration"""
    NORMAL = "normal"
    DELAYED = "delayed"
    DISRUPTED = "disrupted"
    SUSPENDED = "suspended"
    MAINTENANCE = "maintenance"

class DisruptionSeverity(str, Enum):
    """Disruption severity levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

class WeatherCondition(str, Enum):
    """Weather conditions affecting schedules"""
    CLEAR = "clear"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"
    FOG = "fog"
    EXTREME_HEAT = "extreme_heat"

class CrowdLevel(str, Enum):
    """Crowd density levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    OVERCROWDED = "overcrowded"

# Schedule Models
class TrainScheduleBase(BaseModel):
    """Base train schedule model"""
    line_id: int
    station_id: int
    direction: Literal["inbound", "outbound"]
    schedule_type: ScheduleType
    start_time: time
    end_time: time
    frequency_minutes: int  # How often trains arrive
    is_active: bool = True

class TrainSchedule(TrainScheduleBase):
    """Train schedule with timestamps"""
    id: int
    created_at: datetime
    updated_at: datetime

class ScheduleVariation(BaseModel):
    """Schedule variations for different time periods"""
    id: int
    schedule_id: int
    time_period: Literal["rush_hour", "off_peak", "late_night"]
    start_time: time
    end_time: time
    frequency_adjustment: int  # Minutes to add/subtract from base frequency
    capacity_multiplier: float = 1.0  # Adjust for more/fewer trains
    is_active: bool = True

# Departure Predictions
class DeparturePrediction(BaseModel):
    """Predicted departure time for a train"""
    station_id: int
    line_id: int
    direction: Literal["inbound", "outbound"]
    scheduled_time: datetime
    predicted_time: datetime
    delay_minutes: int
    confidence_level: float = Field(..., ge=0, le=1)  # 0-1 confidence score
    last_updated: datetime

class StationSchedule(BaseModel):
    """Complete schedule information for a station"""
    station_id: int
    station_name: str
    departures: List[DeparturePrediction]
    next_arrival: Optional[DeparturePrediction] = None
    service_alerts: List['ServiceAlert'] = []
    crowd_level: CrowdLevel = CrowdLevel.MODERATE
    last_updated: datetime

class LineSchedule(BaseModel):
    """Schedule information for an entire line"""
    line_id: int
    line_name: str
    service_status: ServiceStatus = ServiceStatus.NORMAL
    current_frequency: int  # Current frequency in minutes
    average_delay: int = 0  # Average delay across the line in minutes
    stations: List[StationSchedule] = []
    service_alerts: List['ServiceAlert'] = []
    last_updated: datetime

# Service Status and Alerts
class ServiceAlert(BaseModel):
    """Service alert/disruption information"""
    id: int
    title: str
    description: str
    alert_type: Literal["delay", "disruption", "maintenance", "information", "emergency"]
    severity: DisruptionSeverity
    affected_lines: List[int] = []
    affected_stations: List[int] = []
    start_time: datetime
    end_time: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

class ServiceStatusUpdate(BaseModel):
    """Service status update request"""
    line_id: Optional[int] = None
    station_id: Optional[int] = None
    status: ServiceStatus
    reason: Optional[str] = None
    estimated_resolution: Optional[datetime] = None
    affects_entire_line: bool = False

class ServiceStatusResponse(BaseModel):
    """Service status response with current conditions"""
    line_id: Optional[int]
    station_id: Optional[int]
    status: ServiceStatus
    description: str
    alerts: List[ServiceAlert] = []
    last_updated: datetime
    estimated_resolution: Optional[datetime] = None

# Real-time Data Models
class RealTimeUpdate(BaseModel):
    """Real-time update for trains and stations"""
    update_id: str
    timestamp: datetime
    update_type: Literal["departure", "arrival", "delay", "cancellation", "platform_change"]
    train_id: Optional[str] = None
    line_id: int
    station_id: int
    original_time: datetime
    updated_time: Optional[datetime] = None
    delay_minutes: int = 0
    reason: Optional[str] = None
    platform: Optional[str] = None

class TrainPosition(BaseModel):
    """Current position and status of a train"""
    train_id: str
    line_id: int
    current_station_id: Optional[int] = None
    next_station_id: Optional[int] = None
    direction: Literal["inbound", "outbound"]
    estimated_arrival: Optional[datetime] = None
    delay_minutes: int = 0
    occupancy_level: CrowdLevel = CrowdLevel.MODERATE
    status: Literal["in_service", "out_of_service", "approaching", "at_station", "departed"]
    last_updated: datetime

class CrowdData(BaseModel):
    """Crowd density data for stations and trains"""
    station_id: Optional[int] = None
    train_id: Optional[str] = None
    crowd_level: CrowdLevel
    occupancy_percentage: int = Field(..., ge=0, le=100)
    estimated_wait_time: Optional[int] = None  # Minutes
    peak_times: List[str] = []  # Time ranges when most crowded
    last_updated: datetime

class WeatherImpact(BaseModel):
    """Weather impact on train services"""
    condition: WeatherCondition
    severity: int = Field(..., ge=1, le=5)  # 1-5 scale
    affected_lines: List[int] = []
    impact_description: str
    delay_factor: float = Field(..., ge=1.0, le=3.0)  # Multiplier for delays
    service_reduction: float = Field(..., ge=0.0, le=1.0)  # 0-1, reduction in service
    start_time: datetime
    end_time: Optional[datetime] = None

# Maintenance Scheduling
class MaintenanceWindow(BaseModel):
    """Scheduled maintenance window"""
    id: int
    title: str
    description: str
    maintenance_type: Literal["routine", "emergency", "upgrade", "repair"]
    affected_lines: List[int] = []
    affected_stations: List[int] = []
    start_time: datetime
    end_time: datetime
    impact_level: Literal["minor", "moderate", "major"]
    alternative_routes: List[str] = []
    is_active: bool = True
    created_at: datetime

class MaintenanceScheduleRequest(BaseModel):
    """Request to schedule maintenance"""
    title: str
    description: str
    maintenance_type: Literal["routine", "emergency", "upgrade", "repair"]
    affected_lines: List[int] = []
    affected_stations: List[int] = []
    start_time: datetime
    end_time: datetime
    impact_level: Literal["minor", "moderate", "major"]
    notify_users: bool = True

# API Response Models
class ScheduleResponse(BaseModel):
    """Response for schedule queries"""
    station_id: Optional[int] = None
    line_id: Optional[int] = None
    current_time: datetime
    schedules: List[TrainSchedule] = []
    departures: List[DeparturePrediction] = []
    service_status: ServiceStatus = ServiceStatus.NORMAL
    alerts: List[ServiceAlert] = []
    crowd_info: Optional[CrowdData] = None
    weather_impact: Optional[WeatherImpact] = None

class ServiceStatusFilter(BaseModel):
    """Filters for service status queries"""
    line_ids: Optional[List[int]] = None
    station_ids: Optional[List[int]] = None
    alert_types: Optional[List[str]] = None
    severity: Optional[DisruptionSeverity] = None
    active_only: bool = True
    include_resolved: bool = False

# Statistics and Analytics
class SchedulePerformance(BaseModel):
    """Schedule performance metrics"""
    line_id: Optional[int] = None
    station_id: Optional[int] = None
    date_range_start: datetime
    date_range_end: datetime
    on_time_percentage: float
    average_delay_minutes: float
    total_departures: int
    cancelled_departures: int
    peak_hour_performance: float
    off_peak_performance: float

class ScheduleAnalytics(BaseModel):
    """Analytics for schedule optimization"""
    most_delayed_stations: List[Dict[str, Any]] = []
    busiest_times: List[Dict[str, Any]] = []
    weather_correlations: List[Dict[str, Any]] = []
    maintenance_impact: List[Dict[str, Any]] = []
    crowd_patterns: List[Dict[str, Any]] = []
    recommendations: List[str] = []

# Forward reference resolution
StationSchedule.model_rebuild()
LineSchedule.model_rebuild()