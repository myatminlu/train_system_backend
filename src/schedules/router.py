from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, WebSocket
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, date

from src.database import get_db
from src.schedules.schemas import (
    StationSchedule, LineSchedule, ScheduleResponse, ServiceStatusFilter,
    ServiceStatusResponse, ServiceStatusUpdate, ServiceAlert, MaintenanceWindow,
    MaintenanceScheduleRequest, DisruptionSeverity, SchedulePerformance
)
from src.schedules.service import ScheduleCalculationService
from src.schedules.service_status import ServiceStatusManager
from src.schedules.realtime_service import realtime_simulator
from src.schedules.websocket import websocket_endpoint

router = APIRouter()

@router.get("/station/{station_id}", response_model=ScheduleResponse)
def get_station_schedule(
    station_id: int,
    hours_ahead: int = Query(2, ge=1, le=12, description="Hours ahead to show"),
    include_alerts: bool = Query(True, description="Include service alerts"),
    db: Session = Depends(get_db)
):
    """Get schedule and real-time information for a specific station"""
    
    # Verify station exists
    from src.models import Station
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station with ID {station_id} not found"
        )
    
    schedule_service = ScheduleCalculationService(db)
    status_manager = ServiceStatusManager(db)
    
    # Get departures
    departures = schedule_service.calculate_departures_for_station(
        station_id, hours_ahead=hours_ahead
    )
    
    # Get service status
    service_status_response = status_manager.get_service_status(station_id=station_id)
    
    # Get crowd data
    crowd_data = None
    crowd_info = realtime_simulator.get_crowd_data(station_id)
    if crowd_info:
        crowd_data = crowd_info[0]
    
    # Get weather impact
    weather_impact = None
    if station.line_id:
        weather_conditions = realtime_simulator.get_weather_conditions(station.line_id)
        if weather_conditions:
            weather_impact = weather_conditions[0]
    
    response = ScheduleResponse(
        station_id=station_id,
        current_time=datetime.now(),
        departures=departures,
        service_status=service_status_response.status,
        alerts=service_status_response.alerts if include_alerts else [],
        crowd_info=crowd_data,
        weather_impact=weather_impact
    )
    
    return response

@router.get("/line/{line_id}", response_model=LineSchedule)
def get_line_schedule(
    line_id: int,
    include_stations: bool = Query(True, description="Include station details"),
    db: Session = Depends(get_db)
):
    """Get complete schedule information for a train line"""
    
    # Verify line exists
    from src.models import TrainLine
    line = db.query(TrainLine).filter(TrainLine.id == line_id).first()
    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Line with ID {line_id} not found"
        )
    
    schedule_service = ScheduleCalculationService(db)
    line_schedule = schedule_service.get_line_schedule(line_id)
    
    if not line_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule not found for line {line_id}"
        )
    
    # Optionally exclude station details for lighter response
    if not include_stations:
        line_schedule.stations = []
    
    return line_schedule

@router.get("/departures/next")
def get_next_departures(
    station_ids: str = Query(..., description="Comma-separated station IDs"),
    limit: int = Query(5, ge=1, le=20, description="Number of departures per station"),
    db: Session = Depends(get_db)
):
    """Get next departures for multiple stations"""
    
    try:
        station_id_list = [int(x.strip()) for x in station_ids.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid station_ids format. Use comma-separated integers."
        )
    
    if len(station_id_list) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 stations allowed per request"
        )
    
    schedule_service = ScheduleCalculationService(db)
    results = {}
    
    for station_id in station_id_list:
        departures = schedule_service.calculate_departures_for_station(
            station_id, hours_ahead=1
        )
        results[station_id] = departures[:limit]
    
    return {
        "stations": results,
        "timestamp": datetime.now()
    }

@router.get("/service-status", response_model=List[ServiceStatusResponse])
def get_service_status(
    line_ids: Optional[str] = Query(None, description="Comma-separated line IDs"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    alert_types: Optional[str] = Query(None, description="Comma-separated alert types"),
    severity: Optional[DisruptionSeverity] = Query(None, description="Minimum severity level"),
    active_only: bool = Query(True, description="Show only active alerts"),
    db: Session = Depends(get_db)
):
    """Get service status with optional filters"""
    
    # Parse query parameters
    line_ids_list = None
    if line_ids:
        try:
            line_ids_list = [int(x.strip()) for x in line_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid line_ids format"
            )
    
    station_ids_list = None
    if station_ids:
        try:
            station_ids_list = [int(x.strip()) for x in station_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid station_ids format"
            )
    
    alert_types_list = None
    if alert_types:
        alert_types_list = [x.strip() for x in alert_types.split(",")]
    
    status_manager = ServiceStatusManager(db)
    
    # If specific lines or stations requested, get their status
    if line_ids_list or station_ids_list:
        results = []
        
        if line_ids_list:
            for line_id in line_ids_list:
                status_response = status_manager.get_service_status(line_id=line_id)
                results.append(status_response)
        
        if station_ids_list:
            for station_id in station_ids_list:
                status_response = status_manager.get_service_status(station_id=station_id)
                results.append(status_response)
        
        return results
    
    # Otherwise, get system-wide status
    system_status = status_manager.get_system_wide_status()
    
    # Convert to response format
    results = []
    for line_id, line_status in system_status["line_statuses"].items():
        results.append(line_status)
    
    return results

@router.post("/service-status", response_model=ServiceStatusResponse)
def update_service_status(
    update: ServiceStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update service status (admin only - would require authentication)"""
    
    status_manager = ServiceStatusManager(db)
    
    try:
        response = status_manager.update_service_status(update)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update service status: {str(e)}"
        )

@router.get("/alerts", response_model=List[ServiceAlert])
def get_service_alerts(
    line_ids: Optional[str] = Query(None, description="Comma-separated line IDs"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    alert_types: Optional[str] = Query(None, description="Comma-separated alert types"),
    severity: Optional[DisruptionSeverity] = Query(None, description="Minimum severity level"),
    active_only: bool = Query(True, description="Show only active alerts"),
    include_resolved: bool = Query(False, description="Include resolved alerts"),
    db: Session = Depends(get_db)
):
    """Get service alerts with filtering options"""
    
    # Parse filters
    filters = ServiceStatusFilter(
        active_only=active_only,
        include_resolved=include_resolved
    )
    
    if line_ids:
        try:
            filters.line_ids = [int(x.strip()) for x in line_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid line_ids format"
            )
    
    if station_ids:
        try:
            filters.station_ids = [int(x.strip()) for x in station_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid station_ids format"
            )
    
    if alert_types:
        filters.alert_types = [x.strip() for x in alert_types.split(",")]
    
    if severity:
        filters.severity = severity
    
    status_manager = ServiceStatusManager(db)
    alerts = status_manager.get_service_alerts(filters)
    
    return alerts

@router.post("/alerts", response_model=ServiceAlert)
def create_service_alert(
    title: str = Query(..., description="Alert title"),
    description: str = Query(..., description="Alert description"),
    alert_type: str = Query(..., description="Alert type (delay, disruption, maintenance, etc.)"),
    severity: DisruptionSeverity = Query(..., description="Alert severity"),
    affected_lines: Optional[str] = Query(None, description="Comma-separated line IDs"),
    affected_stations: Optional[str] = Query(None, description="Comma-separated station IDs"),
    duration_minutes: Optional[int] = Query(None, description="Expected duration in minutes"),
    db: Session = Depends(get_db)
):
    """Create a new service alert (admin only - would require authentication)"""
    
    # Parse affected entities
    affected_lines_list = []
    if affected_lines:
        try:
            affected_lines_list = [int(x.strip()) for x in affected_lines.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid affected_lines format"
            )
    
    affected_stations_list = []
    if affected_stations:
        try:
            affected_stations_list = [int(x.strip()) for x in affected_stations.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid affected_stations format"
            )
    
    status_manager = ServiceStatusManager(db)
    
    try:
        alert = status_manager.create_service_alert(
            title=title,
            description=description,
            alert_type=alert_type,
            severity=severity,
            affected_lines=affected_lines_list,
            affected_stations=affected_stations_list,
            duration_minutes=duration_minutes
        )
        return alert
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create service alert: {str(e)}"
        )

@router.put("/alerts/{alert_id}/resolve")
def resolve_service_alert(
    alert_id: int,
    resolution_note: Optional[str] = Query(None, description="Resolution note"),
    db: Session = Depends(get_db)
):
    """Resolve a service alert (admin only - would require authentication)"""
    
    status_manager = ServiceStatusManager(db)
    
    success = status_manager.resolve_service_alert(alert_id, resolution_note)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active alert with ID {alert_id} not found"
        )
    
    return {"message": "Alert resolved successfully", "alert_id": alert_id}

@router.get("/maintenance", response_model=List[MaintenanceWindow])
def get_maintenance_windows(
    active_only: bool = Query(True, description="Show only active maintenance"),
    upcoming_only: bool = Query(False, description="Show only upcoming maintenance"),
    db: Session = Depends(get_db)
):
    """Get scheduled maintenance windows"""
    
    status_manager = ServiceStatusManager(db)
    maintenance_windows = status_manager.get_maintenance_windows(
        active_only=active_only,
        upcoming_only=upcoming_only
    )
    
    return maintenance_windows

@router.post("/maintenance", response_model=MaintenanceWindow)
def schedule_maintenance(
    request: MaintenanceScheduleRequest,
    db: Session = Depends(get_db)
):
    """Schedule a maintenance window (admin only - would require authentication)"""
    
    # Validate affected lines and stations exist
    if request.affected_lines:
        from src.models import TrainLine
        existing_lines = db.query(TrainLine.id).filter(
            TrainLine.id.in_(request.affected_lines)
        ).all()
        existing_line_ids = [line.id for line in existing_lines]
        
        if len(existing_line_ids) != len(request.affected_lines):
            missing_lines = set(request.affected_lines) - set(existing_line_ids)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lines not found: {list(missing_lines)}"
            )
    
    status_manager = ServiceStatusManager(db)
    
    try:
        maintenance = status_manager.schedule_maintenance(request)
        return maintenance
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule maintenance: {str(e)}"
        )

@router.get("/performance", response_model=SchedulePerformance)
def get_schedule_performance(
    line_id: Optional[int] = Query(None, description="Specific line ID"),
    station_id: Optional[int] = Query(None, description="Specific station ID"),
    days_back: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get schedule performance metrics"""
    
    schedule_service = ScheduleCalculationService(db)
    performance = schedule_service.get_schedule_performance(
        line_id=line_id,
        station_id=station_id,
        days_back=days_back
    )
    
    return performance

@router.get("/system-status")
def get_system_status(db: Session = Depends(get_db)):
    """Get overall system status and health"""
    
    status_manager = ServiceStatusManager(db)
    system_status = status_manager.get_system_wide_status()
    
    # Add real-time metrics
    active_trains = realtime_simulator.get_active_trains()
    crowd_data = realtime_simulator.get_crowd_data()
    weather_conditions = realtime_simulator.get_weather_conditions()
    
    system_status.update({
        "active_trains": len(active_trains),
        "stations_with_crowd_data": len(crowd_data),
        "weather_conditions": len(weather_conditions),
        "real_time_data_age": "< 1 minute"  # Would calculate based on last update
    })
    
    return system_status

@router.post("/alerts/resolve-expired")
def resolve_expired_alerts(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Automatically resolve expired alerts (admin maintenance task)"""
    
    status_manager = ServiceStatusManager(db)
    
    def cleanup_task():
        resolved_count = status_manager.auto_resolve_expired_alerts()
        print(f"Auto-resolved {resolved_count} expired alerts")
    
    background_tasks.add_task(cleanup_task)
    
    return {"message": "Expired alert cleanup task scheduled"}

@router.get("/real-time/trains")
def get_real_time_trains(
    line_id: Optional[int] = Query(None, description="Filter by line ID"),
    db: Session = Depends(get_db)
):
    """Get real-time train positions and status"""
    
    trains = realtime_simulator.get_active_trains(line_id=line_id)
    
    return {
        "trains": trains,
        "total_count": len(trains),
        "last_updated": datetime.now()
    }

@router.websocket("/ws/real-time")
async def websocket_real_time_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_endpoint(websocket)