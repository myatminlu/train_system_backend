from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

class AdminRole(str, Enum):
    """Admin role enumeration"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    ANALYST = "analyst"

class PermissionType(str, Enum):
    """Permission type enumeration"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"

class AuditAction(str, Enum):
    """Audit action enumeration"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"
    EXECUTE = "execute"
    EXPORT = "export"

class SystemStatus(str, Enum):
    """System status enumeration"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"

# Admin User Management
class AdminUser(BaseModel):
    """Admin user model"""
    id: int
    username: str
    email: str
    full_name: str
    role: AdminRole
    is_active: bool = True
    is_2fa_enabled: bool = False
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    permissions: List[str] = []

class AdminUserCreate(BaseModel):
    """Admin user creation request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)
    full_name: str
    role: AdminRole
    permissions: List[str] = []
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must contain only letters, numbers, hyphens, and underscores')
        return v

class AdminUserUpdate(BaseModel):
    """Admin user update request"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[str]] = None

class AdminLogin(BaseModel):
    """Admin login request"""
    username: str
    password: str
    totp_code: Optional[str] = None  # For 2FA

class AdminLoginResponse(BaseModel):
    """Admin login response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin_user: AdminUser
    permissions: List[str]
    requires_2fa: bool = False

class Admin2FASetup(BaseModel):
    """2FA setup request"""
    secret_key: str
    qr_code_url: str
    backup_codes: List[str]

class Admin2FAVerify(BaseModel):
    """2FA verification request"""
    totp_code: str

# Permission Management
class Permission(BaseModel):
    """Permission model"""
    id: str
    name: str
    description: str
    resource: str  # e.g., "stations", "bookings", "users"
    action: PermissionType
    scope: Optional[str] = None  # e.g., "own", "all", "department"

class RolePermissions(BaseModel):
    """Role permissions mapping"""
    role: AdminRole
    permissions: List[Permission]
    description: str

# System Dashboard
class SystemMetrics(BaseModel):
    """System metrics for dashboard"""
    total_users: int
    active_bookings: int
    daily_revenue: Decimal
    system_uptime: str
    api_response_time: float
    database_connections: int
    cache_hit_rate: float
    error_rate: float
    active_sessions: int

class DashboardData(BaseModel):
    """Dashboard data response"""
    metrics: SystemMetrics
    recent_bookings: List[Dict[str, Any]]
    recent_alerts: List[Dict[str, Any]]
    performance_data: List[Dict[str, Any]]
    top_routes: List[Dict[str, Any]]
    system_status: SystemStatus
    last_updated: datetime

# Station Management
class AdminStationCreate(BaseModel):
    """Admin station creation request"""
    name: str = Field(..., min_length=1, max_length=100)
    lat: Optional[Decimal] = Field(None, ge=-90, le=90)
    long: Optional[Decimal] = Field(None, ge=-180, le=180)
    line_id: int
    zone_number: Optional[int] = Field(None, ge=1, le=10)
    platform_count: int = Field(1, ge=1, le=20)
    is_interchange: bool = False
    status: Literal["active", "inactive", "maintenance"] = "active"

class AdminStationUpdate(BaseModel):
    """Admin station update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    lat: Optional[Decimal] = Field(None, ge=-90, le=90)
    long: Optional[Decimal] = Field(None, ge=-180, le=180)
    line_id: Optional[int] = None
    zone_number: Optional[int] = Field(None, ge=1, le=10)
    platform_count: Optional[int] = Field(None, ge=1, le=20)
    is_interchange: Optional[bool] = None
    status: Optional[Literal["active", "inactive", "maintenance"]] = None

class AdminStationBulkOperation(BaseModel):
    """Bulk station operation request"""
    operation: Literal["update", "delete", "activate", "deactivate"]
    station_ids: List[int]
    update_data: Optional[Dict[str, Any]] = None

class AdminStationImport(BaseModel):
    """Station import request"""
    stations_data: List[Dict[str, Any]]
    validate_only: bool = False
    update_existing: bool = False

# User Management
class AdminUserManagement(BaseModel):
    """User management operations"""
    user_id: int
    action: Literal["activate", "deactivate", "reset_password", "send_verification"]
    reason: Optional[str] = None

class UserAnalytics(BaseModel):
    """User analytics data"""
    total_users: int
    active_users: int
    new_registrations_today: int
    user_growth_rate: float
    top_user_locations: List[Dict[str, Any]]
    user_activity_patterns: List[Dict[str, Any]]

# System Configuration
class SystemConfig(BaseModel):
    """System configuration"""
    key: str
    value: Any
    description: str
    category: str
    is_sensitive: bool = False
    requires_restart: bool = False

class SystemConfigUpdate(BaseModel):
    """System configuration update"""
    configs: List[Dict[str, Any]]

# Audit Logging
class AuditLog(BaseModel):
    """Audit log entry"""
    id: int
    timestamp: datetime
    admin_user_id: Optional[int] = None
    admin_username: Optional[str] = None
    action: AuditAction
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    success: bool
    error_message: Optional[str] = None

class AuditLogFilter(BaseModel):
    """Audit log filtering options"""
    admin_user_id: Optional[int] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    success: Optional[bool] = None
    limit: int = Field(100, ge=1, le=1000)

# Analytics and Reporting
class BookingAnalyticsRequest(BaseModel):
    """Booking analytics request"""
    date_from: date
    date_to: date
    group_by: Literal["day", "week", "month"] = "day"
    include_cancelled: bool = False
    line_ids: Optional[List[int]] = None
    station_ids: Optional[List[int]] = None

class BookingAnalyticsResponse(BaseModel):
    """Booking analytics response"""
    total_bookings: int
    total_revenue: Decimal
    average_booking_value: Decimal
    booking_trends: List[Dict[str, Any]]
    revenue_trends: List[Dict[str, Any]]
    popular_routes: List[Dict[str, Any]]
    peak_booking_hours: List[Dict[str, Any]]
    cancellation_rate: float

class RoutePopularityAnalytics(BaseModel):
    """Route popularity analytics"""
    route: str
    from_station_name: str
    to_station_name: str
    booking_count: int
    revenue: Decimal
    average_journey_time: int
    popularity_rank: int
    growth_rate: float

class RevenueReport(BaseModel):
    """Revenue report"""
    period: str
    total_revenue: Decimal
    revenue_by_line: List[Dict[str, Any]]
    revenue_by_passenger_type: List[Dict[str, Any]]
    revenue_trends: List[Dict[str, Any]]
    projected_revenue: Optional[Decimal] = None

# System Health Monitoring
class SystemHealth(BaseModel):
    """System health status"""
    overall_status: SystemStatus
    components: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    last_check: datetime
    uptime: str
    version: str

class HealthCheck(BaseModel):
    """Individual health check result"""
    component: str
    status: SystemStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = {}

class SystemAlert(BaseModel):
    """System alert"""
    id: str
    severity: Literal["low", "medium", "high", "critical"]
    title: str
    message: str
    component: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    is_active: bool = True

# Performance Monitoring
class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    timestamp: datetime
    api_response_time_avg: float
    api_response_time_95th: float
    database_query_time_avg: float
    memory_usage_percent: float
    cpu_usage_percent: float
    disk_usage_percent: float
    active_connections: int
    requests_per_minute: int
    error_rate: float

class PerformanceReport(BaseModel):
    """Performance report"""
    period_start: datetime
    period_end: datetime
    metrics_summary: Dict[str, Any]
    trends: List[Dict[str, Any]]
    recommendations: List[str]
    alerts_triggered: int

# Export and Import
class DataExportRequest(BaseModel):
    """Data export request"""
    data_type: Literal["users", "bookings", "stations", "analytics", "audit_logs"]
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    format: Literal["csv", "json", "xlsx"] = "csv"
    filters: Dict[str, Any] = {}

class DataExportResponse(BaseModel):
    """Data export response"""
    export_id: str
    file_url: str
    file_size_bytes: int
    record_count: int
    created_at: datetime
    expires_at: datetime

class BulkOperationResult(BaseModel):
    """Result of bulk operation"""
    operation_id: str
    total_items: int
    successful_items: int
    failed_items: int
    errors: List[Dict[str, Any]]
    warnings: List[str]
    completed_at: datetime

# Notification Management
class AdminNotification(BaseModel):
    """Admin notification"""
    id: str
    title: str
    message: str
    type: Literal["info", "warning", "error", "success"]
    priority: Literal["low", "medium", "high"]
    created_at: datetime
    read_at: Optional[datetime] = None
    admin_user_id: Optional[int] = None  # None = broadcast to all admins

class NotificationSettings(BaseModel):
    """Notification settings"""
    email_enabled: bool = True
    push_enabled: bool = True
    system_alerts: bool = True
    booking_alerts: bool = True
    performance_alerts: bool = True
    security_alerts: bool = True

# Backup and Maintenance
class BackupStatus(BaseModel):
    """Backup status"""
    last_backup: datetime
    next_backup: datetime
    backup_size_mb: float
    backup_location: str
    status: Literal["success", "failed", "in_progress"]
    retention_days: int

class MaintenanceWindow(BaseModel):
    """Maintenance window"""
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    maintenance_type: Literal["scheduled", "emergency", "upgrade"]
    affected_services: List[str]
    notification_sent: bool = False

# Fare Rule Management
class AdminFareRuleCreate(BaseModel):
    """Admin fare rule creation request"""
    route_id: int
    passenger_type_id: int
    price: Decimal = Field(..., ge=0, decimal_places=2)
    valid_from: date
    valid_to: Optional[date] = None

    @validator('valid_to')
    def validate_dates(cls, v, values):
        if v and 'valid_from' in values and v <= values['valid_from']:
            raise ValueError('valid_to must be after valid_from')
        return v

class AdminFareRuleUpdate(BaseModel):
    """Admin fare rule update request"""
    route_id: Optional[int] = None
    passenger_type_id: Optional[int] = None
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    @validator('valid_to')
    def validate_dates(cls, v, values):
        if v and 'valid_from' in values and values['valid_from'] and v <= values['valid_from']:
            raise ValueError('valid_to must be after valid_from')
        return v

class AdminFareRuleBulkOperation(BaseModel):
    """Bulk fare rule operation request"""
    operation: Literal["update", "delete", "activate", "deactivate"]
    fare_rule_ids: List[int]
    update_data: Optional[Dict[str, Any]] = None

class AdminFareRuleImport(BaseModel):
    """Fare rule import request"""
    fare_rules_data: List[Dict[str, Any]]
    validate_only: bool = False
    update_existing: bool = False

# Company Management
class AdminCompanyCreate(BaseModel):
    """Admin company creation request"""
    name: str = Field(..., min_length=1, max_length=255)
    status: Optional[str] = Field("active", max_length=50)
    region_id: int

class AdminCompanyUpdate(BaseModel):
    """Admin company update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, max_length=50)
    region_id: Optional[int] = None

class AdminCompanyBulkOperation(BaseModel):
    """Bulk company operation request"""
    operation: Literal["update", "delete", "activate", "deactivate"]
    company_ids: List[int]
    update_data: Optional[Dict[str, Any]] = None

class AdminCompanyImport(BaseModel):
    """Company import request"""
    companies_data: List[Dict[str, Any]]
    validate_only: bool = False
    update_existing: bool = False

# Route Management
class AdminRouteCreate(BaseModel):
    """Admin route creation request"""
    from_station_id: int
    to_station_id: int
    distance: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    estimated_duration: Optional[int] = Field(None, ge=0)  # in minutes
    status: Optional[str] = Field("active", max_length=50)

    @validator('to_station_id')
    def validate_different_stations(cls, v, values):
        if 'from_station_id' in values and v == values['from_station_id']:
            raise ValueError('to_station_id must be different from from_station_id')
        return v

class AdminRouteUpdate(BaseModel):
    """Admin route update request"""
    from_station_id: Optional[int] = None
    to_station_id: Optional[int] = None
    distance: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    estimated_duration: Optional[int] = Field(None, ge=0)  # in minutes
    status: Optional[str] = Field(None, max_length=50)

    @validator('to_station_id')
    def validate_different_stations(cls, v, values):
        if v and 'from_station_id' in values and values['from_station_id'] and v == values['from_station_id']:
            raise ValueError('to_station_id must be different from from_station_id')
        return v

class AdminRouteBulkOperation(BaseModel):
    """Bulk route operation request"""
    operation: Literal["update", "delete", "activate", "deactivate"]
    route_ids: List[int]
    update_data: Optional[Dict[str, Any]] = None

class AdminRouteImport(BaseModel):
    """Route import request"""
    routes_data: List[Dict[str, Any]]
    validate_only: bool = False
    update_existing: bool = False

# Train Service Management
class AdminTrainServiceCreate(BaseModel):
    """Admin train service creation request"""
    line_id: int
    service_name: str = Field(..., min_length=1, max_length=100)
    start_time: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')  # HH:MM format
    end_time: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')    # HH:MM format
    frequency_minutes: int = Field(..., ge=1, le=120)  # 1 to 120 minutes
    direction: Optional[str] = Field(None, max_length=50)
    is_active: bool = True

    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values:
            start_hour, start_min = map(int, values['start_time'].split(':'))
            end_hour, end_min = map(int, v.split(':'))
            
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            
            # Handle overnight services
            if end_minutes <= start_minutes:
                end_minutes += 24 * 60  # Add 24 hours for next day
                
            # Ensure reasonable service duration (max 20 hours)
            if (end_minutes - start_minutes) > 20 * 60:
                raise ValueError('Service duration cannot exceed 20 hours')
                
        return v

class AdminTrainServiceUpdate(BaseModel):
    """Admin train service update request"""
    line_id: Optional[int] = None
    service_name: Optional[str] = Field(None, min_length=1, max_length=100)
    start_time: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    end_time: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    frequency_minutes: Optional[int] = Field(None, ge=1, le=120)
    direction: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

    @validator('end_time')
    def validate_end_time(cls, v, values):
        if v and 'start_time' in values and values['start_time']:
            start_hour, start_min = map(int, values['start_time'].split(':'))
            end_hour, end_min = map(int, v.split(':'))
            
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            
            if end_minutes <= start_minutes:
                end_minutes += 24 * 60
                
            if (end_minutes - start_minutes) > 20 * 60:
                raise ValueError('Service duration cannot exceed 20 hours')
                
        return v

class AdminTrainServiceBulkOperation(BaseModel):
    """Bulk train service operation request"""
    operation: Literal["update", "delete", "activate", "deactivate"]
    service_ids: List[int]
    update_data: Optional[Dict[str, Any]] = None

class AdminTrainServiceImport(BaseModel):
    """Train service import request"""
    services_data: List[Dict[str, Any]]
    validate_only: bool = False
    update_existing: bool = False

# Transfer Point Management
class AdminTransferPointCreate(BaseModel):
    """Create transfer point request"""
    station_a_id: int = Field(..., description="ID of the first station")
    station_b_id: int = Field(..., description="ID of the second station")
    walking_time_minutes: int = Field(5, ge=1, le=60, description="Walking time in minutes")
    walking_distance_meters: Optional[int] = Field(None, ge=1, description="Walking distance in meters")
    transfer_fee: Decimal = Field(0.00, ge=0, le=999.99, description="Transfer fee")
    is_active: bool = Field(True, description="Is transfer point active")

    @validator('station_b_id')
    def validate_different_stations(cls, v, values):
        if 'station_a_id' in values and v == values['station_a_id']:
            raise ValueError('Station A and Station B must be different')
        return v

class AdminTransferPointUpdate(BaseModel):
    """Update transfer point request"""
    station_a_id: Optional[int] = Field(None, description="ID of the first station")
    station_b_id: Optional[int] = Field(None, description="ID of the second station")
    walking_time_minutes: Optional[int] = Field(None, ge=1, le=60, description="Walking time in minutes")
    walking_distance_meters: Optional[int] = Field(None, ge=1, description="Walking distance in meters")
    transfer_fee: Optional[Decimal] = Field(None, ge=0, le=999.99, description="Transfer fee")
    is_active: Optional[bool] = Field(None, description="Is transfer point active")

class AdminTransferPointBulkOperation(BaseModel):
    """Bulk transfer point operation request"""
    operation: Literal["update", "delete", "activate", "deactivate"]
    transfer_point_ids: List[int]
    update_data: Optional[Dict[str, Any]] = None

class AdminTransferPointImport(BaseModel):
    """Transfer point import request"""
    transfer_points_data: List[Dict[str, Any]]
    validate_only: bool = False
    update_existing: bool = False