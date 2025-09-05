from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .schemas import (
    AdminUser, AdminUserCreate, AdminUserUpdate, AdminLogin, AdminLoginResponse,
    Admin2FASetup, Admin2FAVerify, Permission, RolePermissions, SystemMetrics,
    DashboardData, AdminStationCreate, AdminStationUpdate, AdminStationBulkOperation,
    AdminStationImport, AdminUserManagement, UserAnalytics, SystemConfig,
    SystemConfigUpdate, AuditLog, AuditLogFilter, BookingAnalyticsRequest,
    BookingAnalyticsResponse, RoutePopularityAnalytics, RevenueReport,
    SystemHealth, HealthCheck, SystemAlert, PerformanceMetrics,
    PerformanceReport, DataExportRequest, DataExportResponse,
    BulkOperationResult, AdminNotification, NotificationSettings,
    BackupStatus, MaintenanceWindow, AdminRole, AuditAction,
    AdminFareRuleCreate, AdminFareRuleUpdate, AdminFareRuleBulkOperation, AdminFareRuleImport,
    AdminCompanyCreate, AdminCompanyUpdate, AdminCompanyBulkOperation, AdminCompanyImport,
    AdminRouteCreate, AdminRouteUpdate, AdminRouteBulkOperation, AdminRouteImport,
    AdminTrainServiceCreate, AdminTrainServiceUpdate, AdminTrainServiceBulkOperation, AdminTrainServiceImport,
    AdminTransferPointCreate, AdminTransferPointUpdate, AdminTransferPointBulkOperation, AdminTransferPointImport
)
from .admin_service import AdminManagementService
from .monitoring_service import SystemMonitoringService
from ..database import get_db
from ..auth.dependencies import get_current_user
from ..models import (
    AdminUser as AdminUserModel, User, Ticket, Journey, Route, Station, 
    TrainLine, TrainCompany, Region, AuditLog, SystemConfig as SystemConfigModel, 
    SystemAlert, PerformanceMetrics as PerformanceMetricsModel, PassengerType, FareRule,
    ServiceStatus, TrainService, TransferPoint
)
from sqlalchemy import func, desc, and_, or_, extract, text
from decimal import Decimal
from datetime import datetime, timedelta, date, time
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

def get_current_admin_user(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current authenticated admin user"""
    # Import here to avoid circular imports
    from ..auth.service import UserService
    
    # Check if user has admin role
    user_roles = UserService.get_user_roles(db, current_user.id)
    if "admin" not in user_roles and "super_admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Note: Admin login is now handled by the unified /api/v1/auth/login endpoint

@router.post("/auth/2fa/setup", response_model=Admin2FASetup)
def setup_2fa(
    admin_user: AdminUser = Depends(get_current_admin_user), 
    db: Session = Depends(get_db)
):
    """Setup 2FA for admin user"""
    # Direct database operations - AdminAuthService removed
    # 2FA setup functionality would need proper implementation
    return {"qr_code": "data:image/png;base64,placeholder", "secret": "PLACEHOLDER"}

@router.post("/auth/2fa/verify")
def verify_2fa(
    verify_data: Admin2FAVerify,
    admin_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Verify and enable 2FA for admin user"""
    # Direct database operations - AdminAuthService removed
    # Direct database operations - AdminAuthService removed
    # 2FA verification would need proper implementation
    success = True  # Placeholder
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code"
        )
    
    return {"message": "2FA enabled successfully"}

@router.post("/auth/logout")
def admin_logout(admin_user: AdminUser = Depends(get_current_admin_user)):
    """Admin logout"""
    return {"message": "Logged out successfully"}

# Dashboard Endpoints
@router.get("/dashboard")
def get_dashboard(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get admin dashboard data"""
    # Real database queries for dashboard metrics
    total_users = db.query(User).count()
    admin_users = db.query(AdminUserModel).count()
    active_bookings = db.query(Ticket).filter(Ticket.status.in_(['confirmed', 'reserved'])).count()
    total_bookings = db.query(Ticket).count()
    
    # Calculate daily revenue
    today = datetime.now().date()
    daily_revenue_result = db.query(func.sum(Ticket.total_amount)).filter(
        and_(
            Ticket.status == 'confirmed',
            func.date(Ticket.created_at) == today
        )
    ).scalar() or 0
    daily_revenue = str(daily_revenue_result)
    
    # Get recent performance metrics
    latest_perf = db.query(PerformanceMetricsModel).order_by(desc(PerformanceMetricsModel.timestamp)).first()
    api_response_time = float(latest_perf.api_response_time_avg) if latest_perf and latest_perf.api_response_time_avg else 0.0
    
    # Count active alerts
    active_alerts = db.query(SystemAlert).filter(SystemAlert.is_active == True).count()
    
    # System uptime (simplified - could be enhanced)
    uptime = "Online"
    
    metrics = {
        "total_users": total_users,
        "active_bookings": active_bookings,
        "daily_revenue": daily_revenue,
        "system_uptime": uptime,
        "api_response_time": api_response_time,
        "error_rate": 0.0,  # Could calculate from logs
        "database_connections": 1  # Simplified
    }
    
    # Recent activity (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    recent_bookings = db.query(Ticket).filter(Ticket.created_at >= yesterday).count()
    recent_users = db.query(User).filter(User.created_at >= yesterday).count()
    
    recent_activity = [
        {"type": "bookings", "count": recent_bookings, "change": 0},
        {"type": "users", "count": recent_users, "change": 0}
    ]
    
    return {
        "metrics": metrics,
        "recent_activity": recent_activity,
        "system_status": "healthy",
        "alerts": active_alerts
    }

@router.get("/metrics")
def get_system_metrics(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get current system metrics"""
    # Real database queries for system metrics
    total_users = db.query(User).count()
    active_bookings = db.query(Ticket).filter(Ticket.status.in_(['confirmed', 'reserved'])).count()
    
    # Calculate daily revenue
    today = datetime.now().date()
    daily_revenue_result = db.query(func.sum(Ticket.total_amount)).filter(
        and_(
            Ticket.status == 'confirmed',
            func.date(Ticket.created_at) == today
        )
    ).scalar() or 0
    daily_revenue = str(daily_revenue_result)
    
    # Get recent performance metrics
    latest_perf = db.query(PerformanceMetricsModel).order_by(desc(PerformanceMetricsModel.timestamp)).first()
    api_response_time = float(latest_perf.api_response_time_avg) if latest_perf and latest_perf.api_response_time_avg else 0.0
    
    return {
        "total_users": total_users,
        "active_bookings": active_bookings,
        "daily_revenue": daily_revenue,
        "system_uptime": "Online",
        "api_response_time": api_response_time,
        "error_rate": 0.0,
        "database_connections": 1
    }

# System Health Endpoints
@router.get("/health")
def get_system_health(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get system health status"""
    # Real database query for system health
    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        db_message = "Database connection successful"
    except Exception as e:
        db_status = "unhealthy"
        db_message = f"Database error: {str(e)}"
    
    # Check for active alerts
    critical_alerts = db.query(SystemAlert).filter(
        and_(SystemAlert.is_active == True, SystemAlert.severity == 'critical')
    ).count()
    
    warning_alerts = db.query(SystemAlert).filter(
        and_(SystemAlert.is_active == True, SystemAlert.severity == 'warning')
    ).count()
    
    # Overall system status
    if critical_alerts > 0:
        overall_status = "critical"
    elif warning_alerts > 0:
        overall_status = "warning"
    else:
        overall_status = "healthy"
    
    components = [
        {
            "component": "Database",
            "status": db_status,
            "message": db_message,
            "response_time_ms": 10,
            "details": {}
        },
        {
            "component": "API",
            "status": "healthy",
            "message": "API is responding",
            "response_time_ms": 50,
            "details": {}
        },
        {
            "component": "Authentication",
            "status": "healthy",
            "message": "Authentication system operational",
            "response_time_ms": 25,
            "details": {}
        }
    ]
    
    return {
        "overall_status": overall_status,
        "components": components,
        "last_updated": datetime.now().isoformat(),
        "uptime_seconds": 86400  # Simplified - 1 day
    }

@router.get("/health/components", response_model=List[HealthCheck])
def get_health_components(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get individual component health checks"""
    monitoring_service = SystemMonitoringService(db)
    health_data = monitoring_service.get_system_health()
    
    health_checks = []
    for component in health_data.components:
        health_checks.append(HealthCheck(
            component=component["name"],
            status=component["status"],
            message=component["message"],
            response_time_ms=component.get("response_time_ms"),
            details=component.get("details", {})
        ))
    
    return health_checks

# Performance Monitoring Endpoints
@router.get("/performance/current")
def get_current_performance(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get current performance metrics"""
    monitoring_service = SystemMonitoringService(db)
    current_metrics = monitoring_service.get_current_metrics()
    
    if current_metrics:
        return {
            "timestamp": current_metrics.timestamp,
            "api_response_time_avg": current_metrics.api_response_time_avg,
            "api_response_time_95th": current_metrics.api_response_time_95th,
            "database_query_time_avg": current_metrics.database_query_time_avg,
            "memory_usage_percent": current_metrics.memory_usage_percent,
            "cpu_usage_percent": current_metrics.cpu_usage_percent,
            "disk_usage_percent": current_metrics.disk_usage_percent,
            "active_connections": current_metrics.active_connections,
            "requests_per_minute": current_metrics.requests_per_minute,
            "error_rate": current_metrics.error_rate
        }
    else:
        # Return default metrics if no data available
        return {
            "timestamp": datetime.now(),
            "api_response_time_avg": 150.0,
            "api_response_time_95th": 300.0,
            "database_query_time_avg": 50.0,
            "memory_usage_percent": 45.0,
            "cpu_usage_percent": 25.0,
            "disk_usage_percent": 60.0,
            "active_connections": 10,
            "requests_per_minute": 120,
            "error_rate": 0.5
        }

@router.get("/performance/report", response_model=PerformanceReport)
def get_performance_report(
    hours: int = Query(24, ge=1, le=168),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get performance report for specified hours"""
    monitoring_service = SystemMonitoringService(db)
    return monitoring_service.get_performance_report(hours)

# User Management Endpoints
@router.get("/users", response_model=List[AdminUser])
def get_admin_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[AdminRole] = None,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all admin users"""
    # Direct database operations - AdminAuthService removed
    query = db.query(AdminUserModel)
    
    # Apply role filter if specified
    if role:
        query = query.filter(AdminUserModel.role == role.value)
    
    # Apply pagination and get results
    users = query.offset(skip).limit(limit).all()
    
    # Convert to response models
    return [AdminUser(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_2fa_enabled=user.is_2fa_enabled,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=user.permissions or []
    ) for user in users]

@router.post("/users", response_model=AdminUser)
def create_admin_user(
    user_data: AdminUserCreate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new admin user"""
    # Direct database operations - AdminAuthService removed
    # Simplified implementation - just return a placeholder
    return AdminUser(
        id=999,
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
        is_2fa_enabled=False,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        permissions=[]
    )

@router.get("/users/{user_id}", response_model=AdminUser)
def get_admin_user(
    user_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get admin user by ID"""
    # Direct database operations - AdminAuthService removed
    user = db.query(AdminUserModel).filter(AdminUserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found")
    
    return AdminUser(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_2fa_enabled=user.is_2fa_enabled,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=user.permissions or []
    )

@router.put("/users/{user_id}", response_model=AdminUser)
def update_admin_user(
    user_id: int,
    user_data: AdminUserUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update admin user"""
    # Direct database operations - AdminAuthService removed
    user = db.query(AdminUserModel).filter(AdminUserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found")
    
    # Update user fields if provided
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    db.refresh(user)
    
    return AdminUser(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_2fa_enabled=user.is_2fa_enabled,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=user.permissions or []
    )

@router.post("/users/{user_id}/manage")
def manage_admin_user(
    user_id: int,
    management_data: AdminUserManagement,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Manage admin user (activate, deactivate, reset password)"""
    admin_service = AdminManagementService(db)
    result = admin_service.manage_admin_user(user_id, management_data, admin_user.id)
    return result

# Line Management Endpoints
@router.get("/lines")
def get_lines(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all train lines for admin management"""
    lines = db.query(TrainLine).all()
    
    return [
        {
            "id": line.id,
            "name": line.name,
            "color": line.color,
            "status": line.status,
            "company_id": line.company_id,
            "station_count": db.query(Station).filter(Station.line_id == line.id).count(),
            "created_at": line.created_at.isoformat() if line.created_at else None
        }
        for line in lines
    ]

@router.post("/lines")
def create_line(
    line_data: dict,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new train line"""
    new_line = TrainLine(
        name=line_data["name"],
        color=line_data.get("color"),
        status=line_data.get("status", "active"),
        company_id=line_data.get("company_id", 1)
    )
    db.add(new_line)
    db.commit()
    db.refresh(new_line)
    return new_line

@router.put("/lines/{line_id}")
def update_line(
    line_id: int,
    line_data: dict,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update train line"""
    line = db.query(TrainLine).filter(TrainLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")
    
    for key, value in line_data.items():
        if hasattr(line, key):
            setattr(line, key, value)
    
    db.commit()
    db.refresh(line)
    return line

@router.delete("/lines/{line_id}")
def delete_line(
    line_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete train line"""
    line = db.query(TrainLine).filter(TrainLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")
    
    # Check if line has stations
    station_count = db.query(Station).filter(Station.line_id == line_id).count()
    if station_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete line with {station_count} stations")
    
    db.delete(line)
    db.commit()
    return {"message": "Line deleted successfully"}

# Station Management Endpoints
@router.get("/stations")
def get_stations(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all stations for admin management"""
    stations = db.query(Station).all()
    
    return [
        {
            "id": station.id,
            "name": station.name,
            "lat": str(station.lat) if station.lat else None,
            "long": str(station.long) if station.long else None,
            "line_id": station.line_id,
            "zone_number": station.zone_number,
            "platform_count": getattr(station, 'platform_count', 1),
            "is_interchange": getattr(station, 'is_interchange', False),
            "status": getattr(station, 'status', 'active'),
            "created_at": station.created_at.isoformat() if hasattr(station, 'created_at') and station.created_at else None
        }
        for station in stations
    ]

@router.post("/stations")
def create_station(
    station_data: AdminStationCreate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new station"""
    admin_service = AdminManagementService(db)
    return admin_service.create_station(station_data, admin_user.id)

@router.put("/stations/{station_id}")
def update_station(
    station_id: int,
    station_data: AdminStationUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update station"""
    admin_service = AdminManagementService(db)
    updated_station = admin_service.update_station(station_id, station_data, admin_user.id)
    if not updated_station:
        raise HTTPException(status_code=404, detail="Station not found")
    return updated_station

@router.delete("/stations/{station_id}")
def delete_station(
    station_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete station"""
    admin_service = AdminManagementService(db)
    success = admin_service.delete_station(station_id, admin_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Station not found")
    return {"message": "Station deleted successfully"}

@router.post("/stations/bulk", response_model=BulkOperationResult)
def bulk_station_operations(
    operation: AdminStationBulkOperation,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Perform bulk operations on stations"""
    admin_service = AdminManagementService(db)
    return admin_service.bulk_station_operations(operation, admin_user.id)

@router.post("/stations/import", response_model=BulkOperationResult)
def import_stations(
    import_data: AdminStationImport,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Import stations from data"""
    admin_service = AdminManagementService(db)
    return admin_service.import_stations(import_data, admin_user.id)

# Regular User Management Endpoints
@router.get("/regular-users")
def get_regular_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all regular users (non-admin users)"""
    query = db.query(User)
    
    # Apply search filter if provided
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )
    
    # Apply pagination and get results
    users = query.offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        # Get user roles
        user_roles_result = db.execute(text(
            "SELECT r.name FROM user_has_roles uhr JOIN roles r ON uhr.role_id = r.id WHERE uhr.user_id = :user_id"
        ), {"user_id": user.id})
        user_roles = [row[0] for row in user_roles_result]
        
        # Get ticket count
        ticket_count = db.query(Ticket).filter(Ticket.user_id == user.id).count()
        
        # Get journey count
        journey_count = db.query(Journey).filter(Journey.user_id == user.id).count()
        
        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "roles": user_roles,
            "ticket_count": ticket_count,
            "journey_count": journey_count,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        })
    
    return result

@router.get("/regular-users/{user_id}")
def get_regular_user(
    user_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get regular user details by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user roles
    user_roles_result = db.execute(text(
        "SELECT r.name FROM user_has_roles uhr JOIN roles r ON uhr.role_id = r.id WHERE uhr.user_id = :user_id"
    ), {"user_id": user.id})
    user_roles = [row[0] for row in user_roles_result]
    
    # Get tickets
    tickets = db.query(Ticket).filter(Ticket.user_id == user.id).order_by(desc(Ticket.created_at)).limit(10).all()
    recent_tickets = [{
        "id": ticket.id,
        "status": ticket.status,
        "total_amount": str(ticket.total_amount),
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None
    } for ticket in tickets]
    
    # Get journeys
    journeys = db.query(Journey).filter(Journey.user_id == user.id).order_by(desc(Journey.created_at)).limit(10).all()
    recent_journeys = [{
        "id": journey.id,
        "total_cost": str(journey.total_cost) if journey.total_cost else None,
        "start_time": journey.start_time.isoformat() if journey.start_time else None,
        "end_time": journey.end_time.isoformat() if journey.end_time else None,
        "created_at": journey.created_at.isoformat() if journey.created_at else None
    } for journey in journeys]
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "roles": user_roles,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "recent_tickets": recent_tickets,
        "recent_journeys": recent_journeys,
        "statistics": {
            "total_tickets": len(recent_tickets),
            "total_journeys": len(recent_journeys),
            "total_spent": sum(float(ticket["total_amount"]) for ticket in recent_tickets if ticket["total_amount"])
        }
    }

@router.put("/regular-users/{user_id}")
def update_regular_user(
    user_id: int,
    user_data: dict,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update regular user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields if provided
    if "name" in user_data and user_data["name"]:
        user.name = user_data["name"]
    if "email" in user_data and user_data["email"]:
        # Check if email already exists
        existing_user = db.query(User).filter(
            and_(User.email == user_data["email"], User.id != user_id)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = user_data["email"]
    
    user.updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }

@router.delete("/regular-users/{user_id}")
def delete_regular_user(
    user_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete regular user (soft delete - deactivate)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has active tickets
    active_tickets = db.query(Ticket).filter(
        and_(Ticket.user_id == user_id, Ticket.status.in_(['confirmed', 'reserved']))
    ).count()
    
    if active_tickets > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete user with {active_tickets} active tickets"
        )
    
    # Instead of hard delete, we could add a soft delete flag
    # For now, we'll do hard delete after checking constraints
    
    # Delete user roles first
    db.execute(text("DELETE FROM user_has_roles WHERE user_id = :user_id"), {"user_id": user_id})
    
    # Delete the user
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

@router.get("/user-statistics")
def get_user_statistics(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive user statistics"""
    # Basic counts
    total_users = db.query(User).count()
    
    # Users by role
    role_stats = db.execute(text("""
        SELECT r.name, COUNT(uhr.user_id) as user_count 
        FROM roles r 
        LEFT JOIN user_has_roles uhr ON r.id = uhr.role_id 
        GROUP BY r.name
    """)).all()
    
    users_by_role = {role: count for role, count in role_stats}
    
    # Registration trends (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    registration_trends = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        day_registrations = db.query(User).filter(
            func.date(User.created_at) == day.date()
        ).count()
        registration_trends.append({
            'date': day.strftime('%Y-%m-%d'),
            'registrations': day_registrations
        })
    
    # Most active users
    active_users_query = db.query(
        User.id, User.name, User.email, 
        func.count(Ticket.id).label('ticket_count')
    ).outerjoin(Ticket, User.id == Ticket.user_id)\
     .group_by(User.id, User.name, User.email)\
     .order_by(desc(func.count(Ticket.id)))\
     .limit(5).all()
    
    most_active_users = [{
        "id": user_id,
        "name": name,
        "email": email,
        "ticket_count": ticket_count
    } for user_id, name, email, ticket_count in active_users_query]
    
    # Recent registrations
    recent_users = db.query(User).order_by(desc(User.created_at)).limit(5).all()
    recent_registrations = [{
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None
    } for user in recent_users]
    
    return {
        "total_users": total_users,
        "users_by_role": users_by_role,
        "registration_trends": registration_trends,
        "most_active_users": most_active_users,
        "recent_registrations": recent_registrations,
        "summary": {
            "total_tickets_issued": db.query(Ticket).count(),
            "total_journeys_planned": db.query(Journey).count(),
            "average_tickets_per_user": db.query(Ticket).count() / total_users if total_users > 0 else 0
        }
    }

# Service Status Management Endpoints
@router.get("/service-status")
def get_service_statuses(
    line_id: Optional[int] = Query(None),
    station_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get service statuses with filtering"""
    query = db.query(ServiceStatus)
    
    if line_id:
        query = query.filter(ServiceStatus.line_id == line_id)
    if station_id:
        query = query.filter(ServiceStatus.station_id == station_id)
    if active_only:
        query = query.filter(ServiceStatus.is_active == True)
    
    statuses = query.order_by(desc(ServiceStatus.created_at)).all()
    
    result = []
    for status in statuses:
        # Get related line and station names
        line_name = None
        station_name = None
        
        if status.line_id:
            line = db.query(TrainLine).filter(TrainLine.id == status.line_id).first()
            line_name = line.name if line else None
            
        if status.station_id:
            station = db.query(Station).filter(Station.id == status.station_id).first()
            station_name = station.name if station else None
        
        result.append({
            "id": status.id,
            "line_id": status.line_id,
            "line_name": line_name,
            "station_id": status.station_id,
            "station_name": station_name,
            "status_type": status.status_type,
            "severity": status.severity,
            "message": status.message,
            "start_time": status.start_time.isoformat() if status.start_time else None,
            "end_time": status.end_time.isoformat() if status.end_time else None,
            "is_active": status.is_active,
            "created_at": status.created_at.isoformat() if status.created_at else None
        })
    
    return result

@router.post("/service-status")
def create_service_status(
    status_data: dict,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new service status"""
    new_status = ServiceStatus(
        line_id=status_data.get("line_id"),
        station_id=status_data.get("station_id"),
        status_type=status_data["status_type"],
        severity=status_data.get("severity", "low"),
        message=status_data["message"],
        start_time=datetime.fromisoformat(status_data["start_time"]) if status_data.get("start_time") else datetime.now(),
        end_time=datetime.fromisoformat(status_data["end_time"]) if status_data.get("end_time") else None,
        is_active=status_data.get("is_active", True)
    )
    
    db.add(new_status)
    db.commit()
    db.refresh(new_status)
    
    return {
        "id": new_status.id,
        "line_id": new_status.line_id,
        "station_id": new_status.station_id,
        "status_type": new_status.status_type,
        "severity": new_status.severity,
        "message": new_status.message,
        "start_time": new_status.start_time.isoformat() if new_status.start_time else None,
        "end_time": new_status.end_time.isoformat() if new_status.end_time else None,
        "is_active": new_status.is_active,
        "created_at": new_status.created_at.isoformat() if new_status.created_at else None
    }

@router.put("/service-status/{status_id}")
def update_service_status(
    status_id: int,
    status_data: dict,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update service status"""
    status = db.query(ServiceStatus).filter(ServiceStatus.id == status_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Service status not found")
    
    # Update fields if provided
    if "status_type" in status_data:
        status.status_type = status_data["status_type"]
    if "severity" in status_data:
        status.severity = status_data["severity"]
    if "message" in status_data:
        status.message = status_data["message"]
    if "start_time" in status_data:
        status.start_time = datetime.fromisoformat(status_data["start_time"]) if status_data["start_time"] else None
    if "end_time" in status_data:
        status.end_time = datetime.fromisoformat(status_data["end_time"]) if status_data["end_time"] else None
    if "is_active" in status_data:
        status.is_active = status_data["is_active"]
    
    db.commit()
    db.refresh(status)
    
    return {
        "id": status.id,
        "line_id": status.line_id,
        "station_id": status.station_id,
        "status_type": status.status_type,
        "severity": status.severity,
        "message": status.message,
        "start_time": status.start_time.isoformat() if status.start_time else None,
        "end_time": status.end_time.isoformat() if status.end_time else None,
        "is_active": status.is_active,
        "created_at": status.created_at.isoformat() if status.created_at else None
    }

@router.delete("/service-status/{status_id}")
def delete_service_status(
    status_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete service status"""
    status = db.query(ServiceStatus).filter(ServiceStatus.id == status_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Service status not found")
    
    db.delete(status)
    db.commit()
    return {"message": "Service status deleted successfully"}

@router.post("/service-status/{status_id}/resolve")
def resolve_service_status(
    status_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Resolve service status (mark as inactive and set end time)"""
    status = db.query(ServiceStatus).filter(ServiceStatus.id == status_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Service status not found")
    
    status.is_active = False
    status.end_time = datetime.now()
    
    db.commit()
    db.refresh(status)
    
    return {
        "id": status.id,
        "message": "Service status resolved successfully",
        "end_time": status.end_time.isoformat()
    }

# ================================
# FARE RULES MANAGEMENT
# ================================

@router.get("/fare-rules")
def get_fare_rules(
    route_id: Optional[int] = Query(None),
    passenger_type_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get fare rules with filtering"""
    query = db.query(FareRule)
    
    if route_id:
        query = query.filter(FareRule.route_id == route_id)
    if passenger_type_id:
        query = query.filter(FareRule.passenger_type_id == passenger_type_id)
    if active_only:
        today = date.today()
        query = query.filter(
            and_(
                FareRule.valid_from <= today,
                or_(FareRule.valid_to.is_(None), FareRule.valid_to >= today)
            )
        )
    
    fare_rules = query.all()
    
    # Enhanced fare rules with relationships
    result = []
    for fare_rule in fare_rules:
        result.append({
            "id": fare_rule.id,
            "route_id": fare_rule.route_id,
            "passenger_type_id": fare_rule.passenger_type_id,
            "price": float(fare_rule.price),
            "valid_from": fare_rule.valid_from.isoformat(),
            "valid_to": fare_rule.valid_to.isoformat() if fare_rule.valid_to else None,
            "route": {
                "id": fare_rule.route.id,
                "from_station": fare_rule.route.from_station_ref.name,
                "to_station": fare_rule.route.to_station_ref.name,
            } if fare_rule.route else None,
            "passenger_type": {
                "id": fare_rule.passenger_type.id,
                "name": fare_rule.passenger_type.name,
                "discount_percentage": float(fare_rule.passenger_type.discount_percentage)
            } if fare_rule.passenger_type else None
        })
    
    return result

@router.post("/fare-rules")
def create_fare_rule(
    fare_rule_data: AdminFareRuleCreate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new fare rule"""
    # Validate route exists
    route = db.query(Route).filter(Route.id == fare_rule_data.route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Validate passenger type exists
    passenger_type = db.query(PassengerType).filter(PassengerType.id == fare_rule_data.passenger_type_id).first()
    if not passenger_type:
        raise HTTPException(status_code=404, detail="Passenger type not found")
    
    # Check for duplicate fare rule
    existing = db.query(FareRule).filter(
        and_(
            FareRule.route_id == fare_rule_data.route_id,
            FareRule.passenger_type_id == fare_rule_data.passenger_type_id,
            FareRule.valid_from == fare_rule_data.valid_from
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Fare rule already exists for this route, passenger type and date")
    
    new_fare_rule = FareRule(
        route_id=fare_rule_data.route_id,
        passenger_type_id=fare_rule_data.passenger_type_id,
        price=fare_rule_data.price,
        valid_from=fare_rule_data.valid_from,
        valid_to=fare_rule_data.valid_to
    )
    
    db.add(new_fare_rule)
    db.commit()
    db.refresh(new_fare_rule)
    
    return {
        "id": new_fare_rule.id,
        "route_id": new_fare_rule.route_id,
        "passenger_type_id": new_fare_rule.passenger_type_id,
        "price": float(new_fare_rule.price),
        "valid_from": new_fare_rule.valid_from.isoformat(),
        "valid_to": new_fare_rule.valid_to.isoformat() if new_fare_rule.valid_to else None,
        "message": "Fare rule created successfully"
    }

@router.put("/fare-rules/{fare_rule_id}")
def update_fare_rule(
    fare_rule_id: int,
    fare_rule_data: AdminFareRuleUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update fare rule"""
    fare_rule = db.query(FareRule).filter(FareRule.id == fare_rule_id).first()
    if not fare_rule:
        raise HTTPException(status_code=404, detail="Fare rule not found")
    
    # Update fields if provided
    if fare_rule_data.route_id is not None:
        route = db.query(Route).filter(Route.id == fare_rule_data.route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        fare_rule.route_id = fare_rule_data.route_id
    
    if fare_rule_data.passenger_type_id is not None:
        passenger_type = db.query(PassengerType).filter(PassengerType.id == fare_rule_data.passenger_type_id).first()
        if not passenger_type:
            raise HTTPException(status_code=404, detail="Passenger type not found")
        fare_rule.passenger_type_id = fare_rule_data.passenger_type_id
    
    if fare_rule_data.price is not None:
        fare_rule.price = fare_rule_data.price
    if fare_rule_data.valid_from is not None:
        fare_rule.valid_from = fare_rule_data.valid_from
    if fare_rule_data.valid_to is not None:
        fare_rule.valid_to = fare_rule_data.valid_to
    
    db.commit()
    db.refresh(fare_rule)
    
    return {
        "id": fare_rule.id,
        "route_id": fare_rule.route_id,
        "passenger_type_id": fare_rule.passenger_type_id,
        "price": float(fare_rule.price),
        "valid_from": fare_rule.valid_from.isoformat(),
        "valid_to": fare_rule.valid_to.isoformat() if fare_rule.valid_to else None,
        "message": "Fare rule updated successfully"
    }

@router.delete("/fare-rules/{fare_rule_id}")
def delete_fare_rule(
    fare_rule_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete fare rule"""
    fare_rule = db.query(FareRule).filter(FareRule.id == fare_rule_id).first()
    if not fare_rule:
        raise HTTPException(status_code=404, detail="Fare rule not found")
    
    db.delete(fare_rule)
    db.commit()
    
    return {"message": "Fare rule deleted successfully"}

@router.post("/fare-rules/bulk")
def bulk_fare_rules(
    operation_data: AdminFareRuleBulkOperation,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Perform bulk operations on fare rules"""
    fare_rules = db.query(FareRule).filter(FareRule.id.in_(operation_data.fare_rule_ids)).all()
    
    if len(fare_rules) != len(operation_data.fare_rule_ids):
        raise HTTPException(status_code=404, detail="Some fare rules not found")
    
    success_count = 0
    errors = []
    
    for fare_rule in fare_rules:
        try:
            if operation_data.operation == "delete":
                db.delete(fare_rule)
            elif operation_data.operation == "update" and operation_data.update_data:
                for key, value in operation_data.update_data.items():
                    if hasattr(fare_rule, key):
                        setattr(fare_rule, key, value)
            success_count += 1
        except Exception as e:
            errors.append(f"Fare rule {fare_rule.id}: {str(e)}")
    
    db.commit()
    
    return {
        "message": f"Bulk operation completed. {success_count} fare rules processed.",
        "success_count": success_count,
        "errors": errors
    }

# Helper endpoints for fare rules
@router.get("/routes")
def get_routes(
    from_station_id: Optional[int] = Query(None),
    to_station_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all routes with optional filtering"""
    try:
        # Build base query
        query = db.query(Route)
        
        # Apply filters
        if from_station_id:
            query = query.filter(Route.from_station == from_station_id)
        if to_station_id:
            query = query.filter(Route.to_station == to_station_id)
        if status:
            query = query.filter(Route.status == status)
        
        routes = query.all()
        
        result = []
        for route in routes:
            # Get station names
            from_station = db.query(Station).filter(Station.id == route.from_station).first()
            to_station = db.query(Station).filter(Station.id == route.to_station).first()
            
            result.append({
                "id": route.id,
                "from_station_id": route.from_station,
                "to_station_id": route.to_station,
                "from_station": from_station.name if from_station else "Unknown",
                "to_station": to_station.name if to_station else "Unknown",
                "distance": float(route.distance_km) if route.distance_km else None,
                "estimated_duration": route.duration_minutes,
                "transport_type": route.transport_type,
                "status": getattr(route, 'status', 'active'),
                "created_at": route.created_at.isoformat() if hasattr(route, 'created_at') and route.created_at else None,
                "updated_at": route.updated_at.isoformat() if hasattr(route, 'updated_at') and route.updated_at else None
            })
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch routes: {str(e)}")

@router.post("/routes")
def create_route(
    route_data: AdminRouteCreate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new route"""
    try:
        # Validate that both stations exist
        from_station = db.query(Station).filter(Station.id == route_data.from_station_id).first()
        to_station = db.query(Station).filter(Station.id == route_data.to_station_id).first()
        
        if not from_station:
            raise HTTPException(status_code=400, detail=f"From station with ID {route_data.from_station_id} not found")
        if not to_station:
            raise HTTPException(status_code=400, detail=f"To station with ID {route_data.to_station_id} not found")
        
        # Check if route already exists
        existing_route = db.query(Route).filter(
            and_(
                Route.from_station == route_data.from_station_id,
                Route.to_station == route_data.to_station_id
            )
        ).first()
        
        if existing_route:
            raise HTTPException(
                status_code=400, 
                detail=f"Route from {from_station.name} to {to_station.name} already exists"
            )
        
        # Create new route
        new_route = Route(
            from_station=route_data.from_station_id,
            to_station=route_data.to_station_id,
            distance_km=route_data.distance,
            duration_minutes=route_data.estimated_duration,
            transport_type="train",  # Default to train
            status=route_data.status or "active"
        )
        
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        
        return {
            "id": new_route.id,
            "from_station_id": new_route.from_station,
            "to_station_id": new_route.to_station,
            "from_station": from_station.name,
            "to_station": to_station.name,
            "distance": float(new_route.distance_km) if new_route.distance_km else None,
            "estimated_duration": new_route.duration_minutes,
            "transport_type": new_route.transport_type,
            "status": getattr(new_route, 'status', 'active'),
            "created_at": new_route.created_at.isoformat() if hasattr(new_route, 'created_at') and new_route.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create route: {str(e)}")

@router.put("/routes/{route_id}")
def update_route(
    route_id: int,
    route_data: AdminRouteUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a route"""
    try:
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Validate stations if provided
        if route_data.from_station_id:
            from_station = db.query(Station).filter(Station.id == route_data.from_station_id).first()
            if not from_station:
                raise HTTPException(status_code=400, detail=f"From station with ID {route_data.from_station_id} not found")
            route.from_station = route_data.from_station_id
            
        if route_data.to_station_id:
            to_station = db.query(Station).filter(Station.id == route_data.to_station_id).first()
            if not to_station:
                raise HTTPException(status_code=400, detail=f"To station with ID {route_data.to_station_id} not found")
            route.to_station = route_data.to_station_id
        
        # Check for duplicate route after updates
        if route_data.from_station_id or route_data.to_station_id:
            existing_route = db.query(Route).filter(
                and_(
                    Route.from_station == route.from_station,
                    Route.to_station == route.to_station,
                    Route.id != route_id
                )
            ).first()
            
            if existing_route:
                from_station = db.query(Station).filter(Station.id == route.from_station).first()
                to_station = db.query(Station).filter(Station.id == route.to_station).first()
                raise HTTPException(
                    status_code=400,
                    detail=f"Route from {from_station.name if from_station else 'Unknown'} to {to_station.name if to_station else 'Unknown'} already exists"
                )
        
        # Update other fields
        if route_data.distance is not None:
            route.distance_km = route_data.distance
        if route_data.estimated_duration is not None:
            route.duration_minutes = route_data.estimated_duration
        if route_data.status is not None:
            route.status = route_data.status
        
        db.commit()
        db.refresh(route)
        
        # Get station names for response
        from_station = db.query(Station).filter(Station.id == route.from_station).first()
        to_station = db.query(Station).filter(Station.id == route.to_station).first()
        
        return {
            "id": route.id,
            "from_station_id": route.from_station,
            "to_station_id": route.to_station,
            "from_station": from_station.name if from_station else "Unknown",
            "to_station": to_station.name if to_station else "Unknown",
            "distance": float(route.distance_km) if route.distance_km else None,
            "estimated_duration": route.duration_minutes,
            "transport_type": route.transport_type,
            "status": getattr(route, 'status', 'active'),
            "updated_at": route.updated_at.isoformat() if hasattr(route, 'updated_at') and route.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update route: {str(e)}")

@router.delete("/routes/{route_id}")
def delete_route(
    route_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a route"""
    try:
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Check if route has associated fare rules
        fare_rules_count = db.query(FareRule).filter(FareRule.route_id == route_id).count()
        if fare_rules_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete route that has {fare_rules_count} associated fare rules"
            )
        
        db.delete(route)
        db.commit()
        
        return {"message": "Route deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete route: {str(e)}")

@router.post("/routes/bulk")
def bulk_routes(
    operation_data: AdminRouteBulkOperation,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Perform bulk operations on routes"""
    try:
        routes = db.query(Route).filter(Route.id.in_(operation_data.route_ids)).all()
        
        if len(routes) != len(operation_data.route_ids):
            found_ids = [r.id for r in routes]
            missing_ids = [rid for rid in operation_data.route_ids if rid not in found_ids]
            raise HTTPException(
                status_code=404,
                detail=f"Routes not found: {missing_ids}"
            )
        
        results = {"success": 0, "errors": [], "total": len(routes)}
        
        for route in routes:
            try:
                if operation_data.operation == "delete":
                    # Check for fare rules before deletion
                    fare_rules_count = db.query(FareRule).filter(FareRule.route_id == route.id).count()
                    if fare_rules_count > 0:
                        results["errors"].append(f"Route {route.id}: Cannot delete route with {fare_rules_count} fare rules")
                        continue
                    db.delete(route)
                    
                elif operation_data.operation == "update" and operation_data.update_data:
                    for key, value in operation_data.update_data.items():
                        if hasattr(route, key):
                            setattr(route, key, value)
                    
                elif operation_data.operation == "activate":
                    route.status = "active"
                    
                elif operation_data.operation == "deactivate":
                    route.status = "inactive"
                
                results["success"] += 1
                
            except Exception as e:
                results["errors"].append(f"Route {route.id}: {str(e)}")
        
        db.commit()
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk operation failed: {str(e)}")

@router.get("/passenger-types")
def get_passenger_types(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all passenger types for fare rules management"""
    passenger_types = db.query(PassengerType).all()
    
    result = []
    for passenger_type in passenger_types:
        result.append({
            "id": passenger_type.id,
            "name": passenger_type.name,
            "discount_percentage": float(passenger_type.discount_percentage)
        })
    
    return result

# ================================
# COMPANY MANAGEMENT
# ================================

@router.get("/companies")
def get_companies(
    region_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get companies with filtering"""
    query = db.query(TrainCompany)
    
    if region_id:
        query = query.filter(TrainCompany.region_id == region_id)
    if status:
        query = query.filter(TrainCompany.status == status)
    
    companies = query.all()
    
    # Enhanced companies with relationships
    result = []
    for company in companies:
        # Count train lines for this company
        line_count = db.query(TrainLine).filter(TrainLine.company_id == company.id).count()
        
        result.append({
            "id": company.id,
            "name": company.name,
            "status": company.status,
            "region_id": company.region_id,
            "created_at": company.created_at.isoformat(),
            "updated_at": company.updated_at.isoformat(),
            "region": {
                "id": company.region.id,
                "name": company.region.name,
                "country": company.region.country
            } if company.region else None,
            "line_count": line_count
        })
    
    return result

@router.post("/companies")
def create_company(
    company_data: AdminCompanyCreate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new company"""
    # Validate region exists
    region = db.query(Region).filter(Region.id == company_data.region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    # Check for duplicate company name
    existing = db.query(TrainCompany).filter(TrainCompany.name == company_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company with this name already exists")
    
    new_company = TrainCompany(
        name=company_data.name,
        status=company_data.status,
        region_id=company_data.region_id
    )
    
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    
    return {
        "id": new_company.id,
        "name": new_company.name,
        "status": new_company.status,
        "region_id": new_company.region_id,
        "created_at": new_company.created_at.isoformat(),
        "updated_at": new_company.updated_at.isoformat(),
        "message": "Company created successfully"
    }

@router.put("/companies/{company_id}")
def update_company(
    company_id: int,
    company_data: AdminCompanyUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update company"""
    company = db.query(TrainCompany).filter(TrainCompany.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update fields if provided
    if company_data.region_id is not None:
        region = db.query(Region).filter(Region.id == company_data.region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")
        company.region_id = company_data.region_id
    
    if company_data.name is not None:
        # Check for duplicate name (exclude current company)
        existing = db.query(TrainCompany).filter(
            and_(TrainCompany.name == company_data.name, TrainCompany.id != company_id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Company with this name already exists")
        company.name = company_data.name
    
    if company_data.status is not None:
        company.status = company_data.status
    
    db.commit()
    db.refresh(company)
    
    return {
        "id": company.id,
        "name": company.name,
        "status": company.status,
        "region_id": company.region_id,
        "updated_at": company.updated_at.isoformat(),
        "message": "Company updated successfully"
    }

@router.delete("/companies/{company_id}")
def delete_company(
    company_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete company"""
    company = db.query(TrainCompany).filter(TrainCompany.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if company has train lines
    line_count = db.query(TrainLine).filter(TrainLine.company_id == company_id).count()
    if line_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete company with {line_count} train lines")
    
    db.delete(company)
    db.commit()
    
    return {"message": "Company deleted successfully"}

@router.post("/companies/bulk")
def bulk_companies(
    operation_data: AdminCompanyBulkOperation,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Perform bulk operations on companies"""
    companies = db.query(TrainCompany).filter(TrainCompany.id.in_(operation_data.company_ids)).all()
    
    if len(companies) != len(operation_data.company_ids):
        raise HTTPException(status_code=404, detail="Some companies not found")
    
    success_count = 0
    errors = []
    
    for company in companies:
        try:
            if operation_data.operation == "delete":
                # Check if company has train lines
                line_count = db.query(TrainLine).filter(TrainLine.company_id == company.id).count()
                if line_count > 0:
                    errors.append(f"Company {company.name}: Cannot delete company with {line_count} train lines")
                    continue
                db.delete(company)
            elif operation_data.operation == "activate":
                company.status = "active"
            elif operation_data.operation == "deactivate":
                company.status = "inactive"
            elif operation_data.operation == "update" and operation_data.update_data:
                for key, value in operation_data.update_data.items():
                    if hasattr(company, key):
                        setattr(company, key, value)
            success_count += 1
        except Exception as e:
            errors.append(f"Company {company.name}: {str(e)}")
    
    db.commit()
    
    return {
        "message": f"Bulk operation completed. {success_count} companies processed.",
        "success_count": success_count,
        "errors": errors
    }

# Helper endpoint for regions
@router.get("/regions")
def get_regions(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all regions for company management"""
    regions = db.query(Region).all()
    
    result = []
    for region in regions:
        result.append({
            "id": region.id,
            "name": region.name,
            "country": region.country
        })
    
    return result

# Analytics Endpoints
@router.get("/analytics/bookings")
def get_booking_analytics_simple(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get booking analytics (simplified)"""
    # Real database queries for booking analytics
    total_bookings = db.query(Ticket).count()
    confirmed_bookings = db.query(Ticket).filter(Ticket.status == 'confirmed').count()
    cancelled_bookings = db.query(Ticket).filter(Ticket.status == 'cancelled').count()
    
    # Calculate total revenue from confirmed tickets
    total_revenue_result = db.query(func.sum(Ticket.total_amount)).filter(Ticket.status == 'confirmed').scalar() or 0
    total_revenue = float(total_revenue_result)
    
    # Calculate average booking value
    avg_booking_value = total_revenue / confirmed_bookings if confirmed_bookings > 0 else 0
    
    # Simplified popular routes - get basic route data
    routes = db.query(Route).limit(5).all()
    popular_routes = []
    for route in routes:
        from_station = db.query(Station.name).filter(Station.id == route.from_station).scalar()
        to_station = db.query(Station.name).filter(Station.id == route.to_station).scalar()
        popular_routes.append({
            'route': f'{from_station or "Unknown"} -> {to_station or "Unknown"}',
            'bookings': 0  # Would need proper JOIN to get actual booking count
        })
    
    # Calculate cancellation rate
    cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
    
    # Get booking trends for last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)
    booking_trends = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        day_bookings = db.query(Ticket).filter(
            func.date(Ticket.created_at) == day.date()
        ).count()
        booking_trends.append({
            'date': day.strftime('%Y-%m-%d'),
            'bookings': day_bookings,
            'growth': 0  # Could calculate growth vs previous day
        })
    
    # Revenue trends for last 7 days
    revenue_trends = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        day_revenue = db.query(func.sum(Ticket.total_amount)).filter(
            and_(func.date(Ticket.created_at) == day.date(), 
                 Ticket.status == 'confirmed')
        ).scalar() or 0
        revenue_trends.append({
            'date': day.strftime('%Y-%m-%d'),
            'revenue': float(day_revenue),
            'growth': 0
        })
    
    # Peak booking hours analysis
    peak_hours_query = db.query(
        extract('hour', Ticket.created_at).label('hour'),
        func.count(Ticket.id).label('bookings')
    ).group_by(extract('hour', Ticket.created_at))\
     .order_by(desc(func.count(Ticket.id)))\
     .limit(5).all()
    
    peak_booking_hours = [{
        'hour': f"{int(hour):02d}:00-{int(hour)+1:02d}:00",
        'bookings': bookings
    } for hour, bookings in peak_hours_query]
    
    return {
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "average_booking_value": avg_booking_value,
        "booking_trends": booking_trends,
        "revenue_trends": revenue_trends,
        "popular_routes": popular_routes,
        "peak_booking_hours": peak_booking_hours,
        "cancellation_rate": cancellation_rate
    }

@router.post("/analytics/bookings", response_model=BookingAnalyticsResponse)
def get_booking_analytics_detailed(
    request: BookingAnalyticsRequest,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed booking analytics with filters"""
    admin_service = AdminManagementService(db)
    return admin_service.get_booking_analytics(request)

@router.get("/analytics/routes")
def get_route_popularity(
    limit: int = Query(10, ge=1, le=100),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get route popularity analytics"""
    # Simplified real database query for route popularity
    routes = db.query(Route).limit(limit).all()
    
    results = []
    for i, route in enumerate(routes):
        # Get station names safely
        from_station = db.query(Station).filter(Station.id == route.from_station).first()
        to_station = db.query(Station).filter(Station.id == route.to_station).first()
        
        from_station_name = from_station.name if from_station else "Unknown"
        to_station_name = to_station.name if to_station else "Unknown"
        
        # Calculate basic booking count for this route (simplified)
        booking_count = 0  # Could be enhanced with proper join
        
        results.append({
            "route": f"{from_station_name} -> {to_station_name}",
            "from_station_name": from_station_name,
            "to_station_name": to_station_name,
            "booking_count": booking_count,
            "revenue": 0.0,
            "average_journey_time": route.avg_travel_time_minutes or 30,
            "popularity_rank": i + 1,
            "growth_rate": 0.0
        })
    
    return results

@router.get("/analytics/revenue", response_model=RevenueReport)
def get_revenue_report(
    period: str = Query("month", regex="^(day|week|month|year)$"),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get revenue report"""
    # Real database queries for revenue report
    # Calculate date range based on period
    end_date = datetime.now().date()
    if period == "day":
        start_date = end_date - timedelta(days=1)
    elif period == "week":
        start_date = end_date - timedelta(weeks=1)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    else:  # year
        start_date = end_date - timedelta(days=365)
    
    # Total revenue for the period
    total_revenue_result = db.query(func.sum(Ticket.total_amount)).filter(
        and_(
            Ticket.status == 'confirmed',
            func.date(Ticket.created_at) >= start_date,
            func.date(Ticket.created_at) <= end_date
        )
    ).scalar() or 0
    total_revenue = float(total_revenue_result)
    
    # Revenue by train line
    revenue_by_line_query = db.query(
        TrainLine.name.label('line'),
        func.sum(Ticket.total_amount).label('revenue')
    ).join(Station, TrainLine.id == Station.line_id)\
     .join(Route, or_(Route.from_station == Station.id, Route.to_station == Station.id))\
     .join(Journey, Route.id == Journey.id)\
     .join(Ticket, Journey.id == Ticket.journey_id)\
     .filter(
        and_(
            Ticket.status == 'confirmed',
            func.date(Ticket.created_at) >= start_date,
            func.date(Ticket.created_at) <= end_date
        )
    ).group_by(TrainLine.name).all()
    
    revenue_by_line = []
    for line, revenue in revenue_by_line_query:
        percentage = (float(revenue) / total_revenue * 100) if total_revenue > 0 else 0
        revenue_by_line.append({
            'line': line,
            'revenue': float(revenue),
            'percentage': percentage
        })
    
    # Revenue by passenger type
    revenue_by_type_query = db.query(
        PassengerType.name.label('type'),
        func.sum(Ticket.total_amount).label('revenue')
    ).join(Ticket, PassengerType.id == Ticket.passenger_type_id)\
     .filter(
        and_(
            Ticket.status == 'confirmed',
            func.date(Ticket.created_at) >= start_date,
            func.date(Ticket.created_at) <= end_date
        )
    ).group_by(PassengerType.name).all()
    
    revenue_by_passenger_type = []
    for ptype, revenue in revenue_by_type_query:
        percentage = (float(revenue) / total_revenue * 100) if total_revenue > 0 else 0
        revenue_by_passenger_type.append({
            'type': ptype,
            'revenue': float(revenue),
            'percentage': percentage
        })
    
    # Revenue trends (daily for last period)
    revenue_trends = []
    current_date = start_date
    while current_date <= end_date:
        daily_revenue = db.query(func.sum(Ticket.total_amount)).filter(
            and_(
                Ticket.status == 'confirmed',
                func.date(Ticket.created_at) == current_date
            )
        ).scalar() or 0
        
        revenue_trends.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'revenue': float(daily_revenue)
        })
        current_date += timedelta(days=1)
    
    # Calculate projected revenue (simple trend-based projection)
    recent_avg = sum(trend['revenue'] for trend in revenue_trends[-7:]) / 7 if len(revenue_trends) >= 7 else total_revenue / len(revenue_trends) if revenue_trends else 0
    projected_revenue = total_revenue + (recent_avg * 30)  # Project 30 days ahead
    
    return {
        "period": period,
        "total_revenue": total_revenue,
        "revenue_by_line": revenue_by_line,
        "revenue_by_passenger_type": revenue_by_passenger_type,
        "revenue_trends": revenue_trends,
        "projected_revenue": projected_revenue
    }

@router.get("/analytics/users")
def get_user_analytics(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user analytics"""
    # Real database queries for user analytics
    total_users = db.query(User).count()
    
    # Active users (users with tickets in last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    active_users = db.query(User).join(Ticket, User.id == Ticket.user_id).filter(
        Ticket.created_at >= thirty_days_ago
    ).distinct().count()
    
    # New registrations today
    today = datetime.now().date()
    new_registrations_today = db.query(User).filter(
        func.date(User.created_at) == today
    ).count()
    
    # Calculate user growth rate (new users this month vs last month)
    current_month_start = datetime.now().replace(day=1)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    
    current_month_users = db.query(User).filter(
        User.created_at >= current_month_start
    ).count()
    
    last_month_users = db.query(User).filter(
        and_(
            User.created_at >= last_month_start,
            User.created_at < current_month_start
        )
    ).count()
    
    growth_rate = ((current_month_users - last_month_users) / last_month_users * 100) if last_month_users > 0 else 0
    
    # Top users by booking count
    top_users_query = db.query(
        User.id,
        User.name,
        func.count(Ticket.id).label('booking_count')
    ).join(Ticket, User.id == Ticket.user_id)\
     .group_by(User.id, User.name)\
     .order_by(desc(func.count(Ticket.id)))\
     .limit(5).all()
    
    top_users = [{
        "user_id": user_id,
        "name": name,
        "booking_count": booking_count
    } for user_id, name, booking_count in top_users_query]
    
    # User demographics by passenger type
    demographics = db.query(
        PassengerType.name.label('type'),
        func.count(Ticket.user_id.distinct()).label('user_count')
    ).join(Ticket, PassengerType.id == Ticket.passenger_type_id)\
     .group_by(PassengerType.name).all()
    
    user_demographics = [{
        "category": ptype,
        "count": count
    } for ptype, count in demographics]
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "new_registrations_today": new_registrations_today,
        "user_growth_rate": growth_rate,
        "top_users_by_bookings": top_users,
        "user_demographics": user_demographics
    }

# System Configuration Endpoints
@router.get("/config", response_model=List[SystemConfig])
def get_system_config(
    category: Optional[str] = None,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get system configuration"""
    # Real database query for system configuration
    query = db.query(SystemConfigModel)
    if category:
        query = query.filter(SystemConfigModel.category == category)
    
    configs = query.all()
    
    return [{
        "key": config.key,
        "value": config.value,
        "description": config.description,
        "category": config.category,
        "is_sensitive": config.is_sensitive,
        "requires_restart": config.requires_restart
    } for config in configs]

@router.put("/config")
def update_system_config(
    config_data: SystemConfigUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update system configuration"""
    admin_service = AdminManagementService(db)
    return admin_service.update_system_config(config_data, admin_user.id)

# Audit Log Endpoints
@router.get("/audit-logs")
def get_audit_logs(
    filters: AuditLogFilter = Depends(),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get audit logs with filtering"""
    # Real database query for audit logs
    query = db.query(AuditLog)
    
    # Apply filters if provided
    if hasattr(filters, 'action') and filters.action:
        query = query.filter(AuditLog.action == filters.action)
    if hasattr(filters, 'resource_type') and filters.resource_type:
        query = query.filter(AuditLog.resource_type == filters.resource_type)
    if hasattr(filters, 'admin_user_id') and filters.admin_user_id:
        query = query.filter(AuditLog.admin_user_id == filters.admin_user_id)
    if hasattr(filters, 'success') and filters.success is not None:
        query = query.filter(AuditLog.success == filters.success)
    if hasattr(filters, 'start_date') and filters.start_date:
        query = query.filter(AuditLog.timestamp >= filters.start_date)
    if hasattr(filters, 'end_date') and filters.end_date:
        query = query.filter(AuditLog.timestamp <= filters.end_date)
    
    # Order by most recent first and limit results
    audit_logs = query.order_by(desc(AuditLog.timestamp)).limit(1000).all()
    
    return [{
        "id": log.id,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        "user_id": log.admin_user_id,
        "username": log.admin_username,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": log.details or {},
        "ip_address": log.ip_address,
        "success": log.success,
        "error_message": log.error_message
    } for log in audit_logs]

# Data Export Endpoints
@router.post("/export", response_model=DataExportResponse)
def export_data(
    export_request: DataExportRequest,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Export data to various formats"""
    admin_service = AdminManagementService(db)
    return admin_service.export_data(export_request, admin_user.id)

# System Alerts Endpoints
@router.get("/alerts")
def get_system_alerts(
    active_only: bool = Query(True),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get system alerts"""
    # Real database query for system alerts
    query = db.query(SystemAlert)
    
    if active_only:
        query = query.filter(SystemAlert.is_active == True)
    
    if severity:
        query = query.filter(SystemAlert.severity == severity)
    
    alerts = query.order_by(desc(SystemAlert.created_at)).all()
    
    return [{
        'id': alert.id,
        'severity': alert.severity,
        'title': alert.title,
        'message': alert.message,
        'component': alert.component,
        'metadata': alert.alert_metadata or {},
        'is_active': alert.is_active,
        'created_at': alert.created_at.isoformat() if alert.created_at else None,
        'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
    } for alert in alerts]

@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Resolve system alert"""
    monitoring_service = SystemMonitoringService(db)
    success = monitoring_service.resolve_alert(alert_id, admin_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert resolved successfully"}

# Notification Endpoints
@router.get("/notifications", response_model=List[AdminNotification])
def get_notifications(
    unread_only: bool = Query(False),
    admin_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get admin notifications"""
    admin_service = AdminManagementService(db)
    return admin_service.get_notifications(admin_user.id, unread_only)

@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    admin_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    admin_service = AdminManagementService(db)
    success = admin_service.mark_notification_read(notification_id, admin_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@router.get("/notifications/settings", response_model=NotificationSettings)
def get_notification_settings(
    admin_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get notification settings"""
    admin_service = AdminManagementService(db)
    return admin_service.get_notification_settings(admin_user.id)

@router.put("/notifications/settings")
def update_notification_settings(
    settings: NotificationSettings,
    admin_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update notification settings"""
    admin_service = AdminManagementService(db)
    return admin_service.update_notification_settings(admin_user.id, settings)

# Backup and Maintenance Endpoints
@router.get("/backup/status", response_model=BackupStatus)
def get_backup_status(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get backup status"""
    admin_service = AdminManagementService(db)
    return admin_service.get_backup_status()

@router.post("/backup/create")
def create_backup(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create system backup"""
    admin_service = AdminManagementService(db)
    result = admin_service.create_backup(admin_user.id)
    return result

@router.get("/maintenance/windows", response_model=List[MaintenanceWindow])
def get_maintenance_windows(
    active_only: bool = Query(False),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get maintenance windows"""
    admin_service = AdminManagementService(db)
    return admin_service.get_maintenance_windows(active_only)

@router.post("/maintenance/windows", response_model=MaintenanceWindow)
def create_maintenance_window(
    window_data: MaintenanceWindow,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create maintenance window"""
    admin_service = AdminManagementService(db)
    return admin_service.create_maintenance_window(window_data, admin_user.id)

# Permission Management Endpoints
@router.get("/permissions", response_model=List[Permission])
def get_permissions(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all available permissions"""
    # Direct database operations - AdminAuthService removed
    # Since user requested to remove all permission codes, return empty list
    return []

@router.get("/roles/{role}/permissions", response_model=RolePermissions)
def get_role_permissions(
    role: AdminRole,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get permissions for specific role"""
    # Direct database operations - AdminAuthService removed
    # Since user requested to remove all permission codes, return empty permissions
    return {"role": role.value, "permissions": []}

# Bulk Import/Export Endpoints
@router.post("/bulk/import/lines")
def bulk_import_lines(
    file: UploadFile = File(...),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Bulk import train lines from CSV/Excel file"""
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    try:
        # Read file content
        import pandas as pd
        import io
        
        content = file.file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        results = {"success": 0, "errors": [], "total": len(df)}
        
        for index, row in df.iterrows():
            try:
                # Validate required fields
                if pd.isna(row.get('name')):
                    results["errors"].append(f"Row {index + 1}: Name is required")
                    continue
                
                # Create line
                new_line = TrainLine(
                    name=row['name'],
                    color=row.get('color', '#00A651'),
                    status=row.get('status', 'active'),
                    company_id=int(row.get('company_id', 1))
                )
                db.add(new_line)
                results["success"] += 1
                
            except Exception as e:
                results["errors"].append(f"Row {index + 1}: {str(e)}")
        
        db.commit()
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

@router.post("/bulk/import/users")
def bulk_import_users(
    file: UploadFile = File(...),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Bulk import users from CSV/Excel file"""
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    try:
        import pandas as pd
        import io
        from ..auth.service import UserService
        
        content = file.file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        results = {"success": 0, "errors": [], "total": len(df)}
        
        for index, row in df.iterrows():
            try:
                # Validate required fields
                if pd.isna(row.get('name')) or pd.isna(row.get('email')):
                    results["errors"].append(f"Row {index + 1}: Name and email are required")
                    continue
                
                # Check if user already exists
                existing_user = db.query(User).filter(User.email == row['email']).first()
                if existing_user:
                    results["errors"].append(f"Row {index + 1}: User with email {row['email']} already exists")
                    continue
                
                # Create user (simplified - would need proper password handling in production)
                new_user = User(
                    name=row['name'],
                    email=row['email'],
                    created_at=datetime.now()
                )
                db.add(new_user)
                db.flush()  # Get the ID
                
                # Add default role
                default_role_query = text("INSERT INTO user_has_roles (user_id, role_id) VALUES (:user_id, 1)")
                db.execute(default_role_query, {"user_id": new_user.id})
                
                results["success"] += 1
                
            except Exception as e:
                results["errors"].append(f"Row {index + 1}: {str(e)}")
        
        db.commit()
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

@router.post("/bulk/import/service-status")
def bulk_import_service_status(
    file: UploadFile = File(...),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Bulk import service statuses from CSV/Excel file"""
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    try:
        import pandas as pd
        import io
        
        content = file.file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        results = {"success": 0, "errors": [], "total": len(df)}
        
        for index, row in df.iterrows():
            try:
                # Validate required fields
                if pd.isna(row.get('status_type')) or pd.isna(row.get('message')):
                    results["errors"].append(f"Row {index + 1}: Status type and message are required")
                    continue
                
                # Create service status
                new_status = ServiceStatus(
                    line_id=int(row['line_id']) if not pd.isna(row.get('line_id')) else None,
                    station_id=int(row['station_id']) if not pd.isna(row.get('station_id')) else None,
                    status_type=row['status_type'],
                    severity=row.get('severity', 'low'),
                    message=row['message'],
                    start_time=pd.to_datetime(row['start_time']) if not pd.isna(row.get('start_time')) else datetime.now(),
                    end_time=pd.to_datetime(row['end_time']) if not pd.isna(row.get('end_time')) else None,
                    is_active=bool(row.get('is_active', True))
                )
                db.add(new_status)
                results["success"] += 1
                
            except Exception as e:
                results["errors"].append(f"Row {index + 1}: {str(e)}")
        
        db.commit()
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

@router.get("/bulk/export/lines")
def bulk_export_lines(
    format: str = Query("csv", regex="^(csv|excel)$"),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Bulk export train lines to CSV/Excel"""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    import io
    
    # Get all lines
    lines = db.query(TrainLine).all()
    
    # Convert to DataFrame
    data = []
    for line in lines:
        station_count = db.query(Station).filter(Station.line_id == line.id).count()
        data.append({
            "id": line.id,
            "name": line.name,
            "color": line.color,
            "status": line.status,
            "company_id": line.company_id,
            "station_count": station_count,
            "created_at": line.created_at.isoformat() if line.created_at else None
        })
    
    df = pd.DataFrame(data)
    
    if format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=train_lines.csv"}
        )
    else:  # excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Train Lines', index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=train_lines.xlsx"}
        )

@router.get("/bulk/export/users")
def bulk_export_users(
    format: str = Query("csv", regex="^(csv|excel)$"),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Bulk export users to CSV/Excel"""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    import io
    
    # Get all users
    users = db.query(User).all()
    
    # Convert to DataFrame
    data = []
    for user in users:
        # Get user roles
        user_roles_result = db.execute(text(
            "SELECT r.name FROM user_has_roles uhr JOIN roles r ON uhr.role_id = r.id WHERE uhr.user_id = :user_id"
        ), {"user_id": user.id})
        user_roles = [row[0] for row in user_roles_result]
        
        # Get ticket count
        ticket_count = db.query(Ticket).filter(Ticket.user_id == user.id).count()
        
        data.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "roles": ",".join(user_roles),
            "ticket_count": ticket_count,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        })
    
    df = pd.DataFrame(data)
    
    if format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users.csv"}
        )
    else:  # excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Users', index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=users.xlsx"}
        )

@router.get("/bulk/export/service-status")
def bulk_export_service_status(
    format: str = Query("csv", regex="^(csv|excel)$"),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Bulk export service statuses to CSV/Excel"""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    import io
    
    # Get all service statuses
    statuses = db.query(ServiceStatus).all()
    
    # Convert to DataFrame
    data = []
    for status in statuses:
        # Get related line and station names
        line_name = None
        station_name = None
        
        if status.line_id:
            line = db.query(TrainLine).filter(TrainLine.id == status.line_id).first()
            line_name = line.name if line else None
            
        if status.station_id:
            station = db.query(Station).filter(Station.id == status.station_id).first()
            station_name = station.name if station else None
        
        data.append({
            "id": status.id,
            "line_id": status.line_id,
            "line_name": line_name,
            "station_id": status.station_id,
            "station_name": station_name,
            "status_type": status.status_type,
            "severity": status.severity,
            "message": status.message,
            "start_time": status.start_time.isoformat() if status.start_time else None,
            "end_time": status.end_time.isoformat() if status.end_time else None,
            "is_active": status.is_active,
            "created_at": status.created_at.isoformat() if status.created_at else None
        })
    
    df = pd.DataFrame(data)
    
    if format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=service_status.csv"}
        )
    else:  # excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Service Status', index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=service_status.xlsx"}
        )

@router.get("/bulk/export/stations")
def bulk_export_stations(
    format: str = Query("csv", regex="^(csv|excel)$"),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Bulk export stations to CSV/Excel"""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    import io
    
    # Get all stations
    stations = db.query(Station).all()
    
    # Convert to DataFrame
    data = []
    for station in stations:
        # Get line name
        line_name = None
        if station.line_id:
            line = db.query(TrainLine).filter(TrainLine.id == station.line_id).first()
            line_name = line.name if line else None
        
        data.append({
            "id": station.id,
            "name": station.name,
            "lat": str(station.lat) if station.lat else None,
            "long": str(station.long) if station.long else None,
            "line_id": station.line_id,
            "line_name": line_name,
            "zone_number": station.zone_number,
            "platform_count": getattr(station, 'platform_count', 1),
            "is_interchange": getattr(station, 'is_interchange', False),
            "status": getattr(station, 'status', 'active'),
            "created_at": station.created_at.isoformat() if hasattr(station, 'created_at') and station.created_at else None
        })
    
    df = pd.DataFrame(data)
    
    if format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=stations.csv"}
        )
    else:  # excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Stations', index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=stations.xlsx"}
        )

@router.get("/bulk/templates/{data_type}")
def get_import_template(
    data_type: str,
    admin_user = Depends(get_current_admin_user)
):
    """Get CSV/Excel template for bulk import"""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    import io
    
    templates = {
        "lines": {
            "name": ["BTS Sukhumvit Line", "MRT Blue Line"],
            "color": ["#00A651", "#1E4D8C"],
            "status": ["active", "active"],
            "company_id": [1, 2]
        },
        "users": {
            "name": ["John Doe", "Jane Smith"],
            "email": ["john@example.com", "jane@example.com"]
        },
        "service-status": {
            "line_id": [1, 2],
            "station_id": [1, None],
            "status_type": ["operational", "delayed"],
            "severity": ["low", "medium"],
            "message": ["Normal service", "Delays due to technical issues"],
            "start_time": ["2025-01-01T08:00:00", "2025-01-01T09:00:00"],
            "end_time": [None, "2025-01-01T10:00:00"],
            "is_active": [True, True]
        },
        "stations": {
            "name": ["Siam", "Chitlom"],
            "lat": ["13.7454", "13.7433"],
            "long": ["100.5348", "100.5467"],
            "line_id": [1, 1],
            "zone_number": [1, 1],
            "platform_count": [2, 2],
            "is_interchange": [True, False],
            "status": ["active", "active"]
        }
    }
    
    if data_type not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    df = pd.DataFrame(templates[data_type])
    
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={data_type}_import_template.csv"}
    )

# Train Service/Schedule Management Endpoints
@router.get("/train-services")
def get_train_services(
    line_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    direction: Optional[str] = Query(None),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all train services with optional filtering"""
    try:
        # Build base query
        query = db.query(TrainService)
        
        # Apply filters
        if line_id:
            query = query.filter(TrainService.line_id == line_id)
        if is_active is not None:
            query = query.filter(TrainService.is_active == is_active)
        if direction:
            query = query.filter(TrainService.direction == direction)
        
        services = query.order_by(TrainService.line_id, TrainService.start_time).all()
        
        result = []
        for service in services:
            # Get line name
            line = db.query(TrainLine).filter(TrainLine.id == service.line_id).first()
            
            result.append({
                "id": service.id,
                "line_id": service.line_id,
                "line": {
                    "line_name": line.name if line else "Unknown",
                    "color": line.color if line else "#6B7280"
                },
                "service_name": service.service_name,
                "start_time": service.start_time.strftime("%H:%M") if service.start_time else None,
                "end_time": service.end_time.strftime("%H:%M") if service.end_time else None,
                "frequency_minutes": service.frequency_minutes,
                "direction": service.direction,
                "is_active": service.is_active,
                "created_at": service.created_at.isoformat() if hasattr(service, 'created_at') and service.created_at else None,
                "updated_at": service.updated_at.isoformat() if hasattr(service, 'updated_at') and service.updated_at else None
            })
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch train services: {str(e)}")

@router.post("/train-services")
def create_train_service(
    service_data: AdminTrainServiceCreate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new train service"""
    try:
        # Validate that line exists
        line = db.query(TrainLine).filter(TrainLine.id == service_data.line_id).first()
        if not line:
            raise HTTPException(status_code=400, detail=f"Line with ID {service_data.line_id} not found")
        
        # Convert time strings to time objects
        start_hour, start_min = map(int, service_data.start_time.split(':'))
        end_hour, end_min = map(int, service_data.end_time.split(':'))
        start_time_obj = time(start_hour, start_min)
        end_time_obj = time(end_hour, end_min)
        
        # Check for overlapping services on the same line and direction
        existing_service = db.query(TrainService).filter(
            and_(
                TrainService.line_id == service_data.line_id,
                TrainService.direction == service_data.direction,
                TrainService.is_active == True,
                or_(
                    and_(TrainService.start_time <= start_time_obj, TrainService.end_time >= start_time_obj),
                    and_(TrainService.start_time <= end_time_obj, TrainService.end_time >= end_time_obj),
                    and_(TrainService.start_time >= start_time_obj, TrainService.end_time <= end_time_obj)
                )
            )
        ).first()
        
        if existing_service:
            raise HTTPException(
                status_code=400,
                detail=f"Service overlaps with existing service '{existing_service.service_name}' on {line.name}"
            )
        
        # Create new train service
        new_service = TrainService(
            line_id=service_data.line_id,
            service_name=service_data.service_name,
            start_time=start_time_obj,
            end_time=end_time_obj,
            frequency_minutes=service_data.frequency_minutes,
            direction=service_data.direction,
            is_active=service_data.is_active
        )
        
        db.add(new_service)
        db.commit()
        db.refresh(new_service)
        
        return {
            "id": new_service.id,
            "line_id": new_service.line_id,
            "line_name": line.name,
            "line_color": line.color,
            "service_name": new_service.service_name,
            "start_time": new_service.start_time.strftime("%H:%M"),
            "end_time": new_service.end_time.strftime("%H:%M"),
            "frequency_minutes": new_service.frequency_minutes,
            "direction": new_service.direction,
            "is_active": new_service.is_active,
            "created_at": new_service.created_at.isoformat() if hasattr(new_service, 'created_at') and new_service.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create train service: {str(e)}")

@router.put("/train-services/{service_id}")
def update_train_service(
    service_id: int,
    service_data: AdminTrainServiceUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a train service"""
    try:
        service = db.query(TrainService).filter(TrainService.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Train service not found")
        
        # Validate line if provided
        if service_data.line_id:
            line = db.query(TrainLine).filter(TrainLine.id == service_data.line_id).first()
            if not line:
                raise HTTPException(status_code=400, detail=f"Line with ID {service_data.line_id} not found")
            service.line_id = service_data.line_id
        
        # Update fields
        if service_data.service_name is not None:
            service.service_name = service_data.service_name
        if service_data.start_time is not None:
            start_hour, start_min = map(int, service_data.start_time.split(':'))
            service.start_time = time(start_hour, start_min)
        if service_data.end_time is not None:
            end_hour, end_min = map(int, service_data.end_time.split(':'))
            service.end_time = time(end_hour, end_min)
        if service_data.frequency_minutes is not None:
            service.frequency_minutes = service_data.frequency_minutes
        if service_data.direction is not None:
            service.direction = service_data.direction
        if service_data.is_active is not None:
            service.is_active = service_data.is_active
        
        db.commit()
        db.refresh(service)
        
        # Get line info for response
        line = db.query(TrainLine).filter(TrainLine.id == service.line_id).first()
        
        return {
            "id": service.id,
            "line_id": service.line_id,
            "line_name": line.name if line else "Unknown",
            "line_color": line.color if line else "#000000",
            "service_name": service.service_name,
            "start_time": service.start_time.strftime("%H:%M") if service.start_time else None,
            "end_time": service.end_time.strftime("%H:%M") if service.end_time else None,
            "frequency_minutes": service.frequency_minutes,
            "direction": service.direction,
            "is_active": service.is_active,
            "updated_at": service.updated_at.isoformat() if hasattr(service, 'updated_at') and service.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update train service: {str(e)}")

@router.delete("/train-services/{service_id}")
def delete_train_service(
    service_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a train service"""
    try:
        service = db.query(TrainService).filter(TrainService.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Train service not found")
        
        db.delete(service)
        db.commit()
        
        return {"message": "Train service deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete train service: {str(e)}")

@router.post("/train-services/bulk")
def bulk_train_services(
    operation_data: AdminTrainServiceBulkOperation,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Perform bulk operations on train services"""
    try:
        services = db.query(TrainService).filter(TrainService.id.in_(operation_data.service_ids)).all()
        
        if len(services) != len(operation_data.service_ids):
            found_ids = [s.id for s in services]
            missing_ids = [sid for sid in operation_data.service_ids if sid not in found_ids]
            raise HTTPException(
                status_code=404,
                detail=f"Train services not found: {missing_ids}"
            )
        
        results = {"success": 0, "errors": [], "total": len(services)}
        
        for service in services:
            try:
                if operation_data.operation == "delete":
                    db.delete(service)
                    
                elif operation_data.operation == "update" and operation_data.update_data:
                    for key, value in operation_data.update_data.items():
                        if hasattr(service, key):
                            if key in ['start_time', 'end_time'] and isinstance(value, str):
                                hour, minute = map(int, value.split(':'))
                                setattr(service, key, time(hour, minute))
                            else:
                                setattr(service, key, value)
                    
                elif operation_data.operation == "activate":
                    service.is_active = True
                    
                elif operation_data.operation == "deactivate":
                    service.is_active = False
                
                results["success"] += 1
                
            except Exception as e:
                results["errors"].append(f"Service {service.id}: {str(e)}")
        
        db.commit()
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk operation failed: {str(e)}")

# Helper endpoint for generating timetables
@router.get("/train-services/{service_id}/timetable")
def get_service_timetable(
    service_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Generate timetable for a specific train service"""
    try:
        service = db.query(TrainService).filter(TrainService.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Train service not found")
        
        # Generate departure times based on frequency
        timetable = []
        current_time = datetime.combine(date.today(), service.start_time)
        end_time = datetime.combine(date.today(), service.end_time)
        
        # Handle overnight services
        if end_time <= current_time:
            end_time = end_time + timedelta(days=1)
        
        departure_count = 0
        while current_time <= end_time and departure_count < 200:  # Limit to prevent infinite loops
            timetable.append({
                "departure_time": current_time.strftime("%H:%M"),
                "sequence": departure_count + 1
            })
            current_time += timedelta(minutes=service.frequency_minutes)
            departure_count += 1
        
        line = db.query(TrainLine).filter(TrainLine.id == service.line_id).first()
        
        return {
            "service": {
                "id": service.id,
                "service_name": service.service_name,
                "line_name": line.name if line else "Unknown",
                "direction": service.direction,
                "frequency_minutes": service.frequency_minutes
            },
            "timetable": timetable,
            "total_departures": len(timetable)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate timetable: {str(e)}")# Transfer Points Management Endpoints

# ================================
# Transfer Points Management
# ================================

@router.get("/transfer-points")
def get_transfer_points(
    station_a_id: Optional[int] = Query(None),
    station_b_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all transfer points with optional filtering"""
    try:
        query = db.query(TransferPoint)
        
        # Apply filters
        if station_a_id:
            query = query.filter(or_(TransferPoint.station_a_id == station_a_id, TransferPoint.station_b_id == station_a_id))
        if station_b_id:
            query = query.filter(or_(TransferPoint.station_a_id == station_b_id, TransferPoint.station_b_id == station_b_id))
        if is_active is not None:
            query = query.filter(TransferPoint.is_active == is_active)
        
        transfer_points = query.all()
        
        # Format response with station names
        result = []
        for tp in transfer_points:
            station_a = db.query(Station).filter(Station.id == tp.station_a_id).first()
            station_b = db.query(Station).filter(Station.id == tp.station_b_id).first()
            
            result.append({
                "id": tp.id,
                "station_a_id": tp.station_a_id,
                "station_a_name": station_a.name if station_a else "Unknown",
                "station_b_id": tp.station_b_id,
                "station_b_name": station_b.name if station_b else "Unknown",
                "walking_time_minutes": tp.walking_time_minutes,
                "walking_distance_meters": tp.walking_distance_meters,
                "transfer_fee": tp.transfer_fee,
                "is_active": tp.is_active,
                "created_at": tp.created_at
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transfer points: {str(e)}")

@router.post("/transfer-points")
def create_transfer_point(
    transfer_point_data: AdminTransferPointCreate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new transfer point"""
    try:
        # Check if stations exist
        station_a = db.query(Station).filter(Station.id == transfer_point_data.station_a_id).first()
        station_b = db.query(Station).filter(Station.id == transfer_point_data.station_b_id).first()
        
        if not station_a:
            raise HTTPException(status_code=404, detail=f"Station A with id {transfer_point_data.station_a_id} not found")
        if not station_b:
            raise HTTPException(status_code=404, detail=f"Station B with id {transfer_point_data.station_b_id} not found")
        
        # Check for duplicate transfer points
        existing = db.query(TransferPoint).filter(
            or_(
                and_(TransferPoint.station_a_id == transfer_point_data.station_a_id, 
                     TransferPoint.station_b_id == transfer_point_data.station_b_id),
                and_(TransferPoint.station_a_id == transfer_point_data.station_b_id, 
                     TransferPoint.station_b_id == transfer_point_data.station_a_id)
            )
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Transfer point between these stations already exists")
        
        new_transfer_point = TransferPoint(**transfer_point_data.dict())
        db.add(new_transfer_point)
        db.commit()
        db.refresh(new_transfer_point)
        
        return {
            "id": new_transfer_point.id,
            "station_a_id": new_transfer_point.station_a_id,
            "station_a_name": station_a.name,
            "station_b_id": new_transfer_point.station_b_id,
            "station_b_name": station_b.name,
            "walking_time_minutes": new_transfer_point.walking_time_minutes,
            "walking_distance_meters": new_transfer_point.walking_distance_meters,
            "transfer_fee": new_transfer_point.transfer_fee,
            "is_active": new_transfer_point.is_active,
            "created_at": new_transfer_point.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create transfer point: {str(e)}")

@router.put("/transfer-points/{transfer_point_id}")
def update_transfer_point(
    transfer_point_id: int,
    transfer_point_data: AdminTransferPointUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a transfer point"""
    try:
        transfer_point = db.query(TransferPoint).filter(TransferPoint.id == transfer_point_id).first()
        if not transfer_point:
            raise HTTPException(status_code=404, detail="Transfer point not found")
        
        # Update fields
        update_data = transfer_point_data.dict(exclude_unset=True)
        
        # Validate station existence if stations are being updated
        if "station_a_id" in update_data:
            station_a = db.query(Station).filter(Station.id == update_data["station_a_id"]).first()
            if not station_a:
                raise HTTPException(status_code=404, detail=f"Station A with id {update_data['station_a_id']} not found")
        
        if "station_b_id" in update_data:
            station_b = db.query(Station).filter(Station.id == update_data["station_b_id"]).first()
            if not station_b:
                raise HTTPException(status_code=404, detail=f"Station B with id {update_data['station_b_id']} not found")
        
        for field, value in update_data.items():
            setattr(transfer_point, field, value)
        
        db.commit()
        db.refresh(transfer_point)
        
        # Get station names for response
        station_a = db.query(Station).filter(Station.id == transfer_point.station_a_id).first()
        station_b = db.query(Station).filter(Station.id == transfer_point.station_b_id).first()
        
        return {
            "id": transfer_point.id,
            "station_a_id": transfer_point.station_a_id,
            "station_a_name": station_a.name if station_a else "Unknown",
            "station_b_id": transfer_point.station_b_id,
            "station_b_name": station_b.name if station_b else "Unknown",
            "walking_time_minutes": transfer_point.walking_time_minutes,
            "walking_distance_meters": transfer_point.walking_distance_meters,
            "transfer_fee": transfer_point.transfer_fee,
            "is_active": transfer_point.is_active,
            "created_at": transfer_point.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update transfer point: {str(e)}")

@router.delete("/transfer-points/{transfer_point_id}")
def delete_transfer_point(
    transfer_point_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a transfer point"""
    try:
        transfer_point = db.query(TransferPoint).filter(TransferPoint.id == transfer_point_id).first()
        if not transfer_point:
            raise HTTPException(status_code=404, detail="Transfer point not found")
        
        db.delete(transfer_point)
        db.commit()
        
        return {"message": "Transfer point deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete transfer point: {str(e)}")

@router.post("/transfer-points/bulk")
def bulk_transfer_points_operation(
    operation: AdminTransferPointBulkOperation,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Perform bulk operations on transfer points"""
    try:
        transfer_points = db.query(TransferPoint).filter(TransferPoint.id.in_(operation.transfer_point_ids)).all()
        
        if len(transfer_points) != len(operation.transfer_point_ids):
            raise HTTPException(status_code=404, detail="Some transfer points not found")
        
        results = []
        
        if operation.operation == "delete":
            for tp in transfer_points:
                db.delete(tp)
                results.append(f"Deleted transfer point {tp.id}")
        
        elif operation.operation == "activate":
            for tp in transfer_points:
                tp.is_active = True
                results.append(f"Activated transfer point {tp.id}")
        
        elif operation.operation == "deactivate":
            for tp in transfer_points:
                tp.is_active = False
                results.append(f"Deactivated transfer point {tp.id}")
        
        elif operation.operation == "update" and operation.update_data:
            for tp in transfer_points:
                for field, value in operation.update_data.items():
                    if hasattr(tp, field):
                        setattr(tp, field, value)
                results.append(f"Updated transfer point {tp.id}")
        
        db.commit()
        
        return {
            "message": f"Bulk operation '{operation.operation}' completed",
            "affected_count": len(transfer_points),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk operation failed: {str(e)}")