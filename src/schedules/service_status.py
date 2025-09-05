from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models import Station, TrainLine
from src.schedules.schemas import (
    ServiceAlert, ServiceStatus, ServiceStatusUpdate, ServiceStatusResponse,
    ServiceStatusFilter, DisruptionSeverity, MaintenanceWindow, MaintenanceScheduleRequest
)
from src.schedules.realtime_service import realtime_simulator

class ServiceStatusManager:
    """Service for managing train service status and alerts"""
    
    def __init__(self, db: Session):
        self.db = db
        self._status_cache: Dict[str, ServiceStatus] = {}
        self._alert_id_counter = 1000
        self._maintenance_id_counter = 2000
        self._notification_callbacks: List[callable] = []
    
    def create_service_alert(
        self, 
        title: str,
        description: str,
        alert_type: str,
        severity: DisruptionSeverity,
        affected_lines: List[int] = None,
        affected_stations: List[int] = None,
        duration_minutes: Optional[int] = None
    ) -> ServiceAlert:
        """Create a new service alert"""
        
        alert_id = self._alert_id_counter
        self._alert_id_counter += 1
        
        start_time = datetime.now()
        end_time = None
        if duration_minutes:
            end_time = start_time + timedelta(minutes=duration_minutes)
        
        alert = ServiceAlert(
            id=alert_id,
            title=title,
            description=description,
            alert_type=alert_type,
            severity=severity,
            affected_lines=affected_lines or [],
            affected_stations=affected_stations or [],
            start_time=start_time,
            end_time=end_time,
            is_active=True,
            created_at=start_time,
            updated_at=start_time
        )
        
        # Add to real-time simulator
        realtime_simulator.service_alerts.append(alert)
        
        # Trigger notifications
        self._trigger_alert_notifications(alert)
        
        return alert
    
    def update_service_alert(self, alert_id: int, updates: Dict) -> Optional[ServiceAlert]:
        """Update an existing service alert"""
        
        # Find alert in simulator
        alert = None
        for existing_alert in realtime_simulator.service_alerts:
            if existing_alert.id == alert_id:
                alert = existing_alert
                break
        
        if not alert:
            return None
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(alert, key):
                setattr(alert, key, value)
        
        alert.updated_at = datetime.now()
        
        # Trigger notifications for update
        self._trigger_alert_notifications(alert, is_update=True)
        
        return alert
    
    def resolve_service_alert(self, alert_id: int, resolution_note: Optional[str] = None) -> bool:
        """Resolve/close a service alert"""
        
        # Find and resolve alert
        for alert in realtime_simulator.service_alerts:
            if alert.id == alert_id and alert.is_active:
                alert.is_active = False
                alert.end_time = datetime.now()
                alert.updated_at = datetime.now()
                
                if resolution_note:
                    alert.description += f" [Resolved: {resolution_note}]"
                
                # Trigger resolution notifications
                self._trigger_resolution_notifications(alert)
                return True
        
        return False
    
    def get_service_alerts(self, filters: ServiceStatusFilter) -> List[ServiceAlert]:
        """Get service alerts based on filters"""
        
        alerts = realtime_simulator.get_service_alerts(active_only=filters.active_only)
        
        # Apply filters
        if filters.line_ids:
            alerts = [a for a in alerts if any(line_id in filters.line_ids 
                     for line_id in a.affected_lines)]
        
        if filters.station_ids:
            alerts = [a for a in alerts if any(station_id in filters.station_ids 
                     for station_id in a.affected_stations)]
        
        if filters.alert_types:
            alerts = [a for a in alerts if a.alert_type in filters.alert_types]
        
        if filters.severity:
            alerts = [a for a in alerts if a.severity == filters.severity]
        
        if not filters.include_resolved:
            alerts = [a for a in alerts if a.is_active]
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    def update_service_status(self, update: ServiceStatusUpdate) -> ServiceStatusResponse:
        """Update service status for a line or station"""
        
        key = f"line_{update.line_id}" if update.line_id else f"station_{update.station_id}"
        self._status_cache[key] = update.status
        
        # Create appropriate alert if status indicates problems
        if update.status in [ServiceStatus.DELAYED, ServiceStatus.DISRUPTED, ServiceStatus.SUSPENDED]:
            severity_map = {
                ServiceStatus.DELAYED: DisruptionSeverity.LOW,
                ServiceStatus.DISRUPTED: DisruptionSeverity.MODERATE,
                ServiceStatus.SUSPENDED: DisruptionSeverity.HIGH
            }
            
            alert_title = f"Service {update.status.value}"
            if update.line_id:
                line = self.db.query(TrainLine).filter(TrainLine.id == update.line_id).first()
                alert_title += f" on {line.name if line else 'Line ' + str(update.line_id)}"
            
            self.create_service_alert(
                title=alert_title,
                description=update.reason or f"Service is currently {update.status.value}",
                alert_type="disruption" if update.status == ServiceStatus.DISRUPTED else "delay",
                severity=severity_map[update.status],
                affected_lines=[update.line_id] if update.line_id else [],
                affected_stations=[update.station_id] if update.station_id else []
            )
        
        # Get current alerts for this service
        filters = ServiceStatusFilter(
            line_ids=[update.line_id] if update.line_id else None,
            station_ids=[update.station_id] if update.station_id else None,
            active_only=True
        )
        current_alerts = self.get_service_alerts(filters)
        
        return ServiceStatusResponse(
            line_id=update.line_id,
            station_id=update.station_id,
            status=update.status,
            description=update.reason or f"Service status: {update.status.value}",
            alerts=current_alerts,
            last_updated=datetime.now(),
            estimated_resolution=update.estimated_resolution
        )
    
    def get_service_status(
        self, 
        line_id: Optional[int] = None, 
        station_id: Optional[int] = None
    ) -> ServiceStatusResponse:
        """Get current service status"""
        
        key = f"line_{line_id}" if line_id else f"station_{station_id}"
        status = self._status_cache.get(key, ServiceStatus.NORMAL)
        
        # Get current alerts
        filters = ServiceStatusFilter(
            line_ids=[line_id] if line_id else None,
            station_ids=[station_id] if station_id else None,
            active_only=True
        )
        current_alerts = self.get_service_alerts(filters)
        
        # Determine status from alerts if not explicitly set
        if status == ServiceStatus.NORMAL and current_alerts:
            if any(a.severity in [DisruptionSeverity.HIGH, DisruptionSeverity.CRITICAL] 
                   for a in current_alerts):
                status = ServiceStatus.DISRUPTED
            elif any(a.severity == DisruptionSeverity.MODERATE for a in current_alerts):
                status = ServiceStatus.DELAYED
        
        description = self._generate_status_description(status, current_alerts)
        
        return ServiceStatusResponse(
            line_id=line_id,
            station_id=station_id,
            status=status,
            description=description,
            alerts=current_alerts,
            last_updated=datetime.now()
        )
    
    def schedule_maintenance(self, request: MaintenanceScheduleRequest) -> MaintenanceWindow:
        """Schedule a maintenance window"""
        
        maintenance_id = self._maintenance_id_counter
        self._maintenance_id_counter += 1
        
        maintenance = MaintenanceWindow(
            id=maintenance_id,
            title=request.title,
            description=request.description,
            maintenance_type=request.maintenance_type,
            affected_lines=request.affected_lines,
            affected_stations=request.affected_stations,
            start_time=request.start_time,
            end_time=request.end_time,
            impact_level=request.impact_level,
            alternative_routes=[],  # Would be calculated based on affected services
            is_active=True,
            created_at=datetime.now()
        )
        
        # Add to simulator
        realtime_simulator.maintenance_windows.append(maintenance)
        
        # Create service alert for maintenance
        if request.notify_users:
            alert_title = f"Scheduled Maintenance: {request.title}"
            
            self.create_service_alert(
                title=alert_title,
                description=f"{request.description} Scheduled from {request.start_time.strftime('%Y-%m-%d %H:%M')} to {request.end_time.strftime('%Y-%m-%d %H:%M')}",
                alert_type="maintenance",
                severity=DisruptionSeverity.LOW if request.impact_level == "minor" 
                        else DisruptionSeverity.MODERATE if request.impact_level == "moderate" 
                        else DisruptionSeverity.HIGH,
                affected_lines=request.affected_lines,
                affected_stations=request.affected_stations,
                duration_minutes=int((request.end_time - request.start_time).total_seconds() / 60)
            )
        
        return maintenance
    
    def get_maintenance_windows(
        self, 
        active_only: bool = True,
        upcoming_only: bool = False
    ) -> List[MaintenanceWindow]:
        """Get maintenance windows"""
        
        windows = realtime_simulator.get_maintenance_windows(active_only=False)
        
        if active_only:
            windows = [w for w in windows if w.is_active]
        
        if upcoming_only:
            current_time = datetime.now()
            windows = [w for w in windows if w.start_time > current_time]
        
        return sorted(windows, key=lambda x: x.start_time)
    
    def auto_resolve_expired_alerts(self):
        """Automatically resolve expired alerts"""
        
        current_time = datetime.now()
        resolved_count = 0
        
        for alert in realtime_simulator.service_alerts:
            if (alert.is_active and alert.end_time and 
                alert.end_time <= current_time):
                
                alert.is_active = False
                alert.updated_at = current_time
                resolved_count += 1
                
                # Trigger resolution notifications
                self._trigger_resolution_notifications(alert)
        
        return resolved_count
    
    def categorize_alerts_by_impact(self) -> Dict[str, List[ServiceAlert]]:
        """Categorize alerts by their impact level"""
        
        alerts = realtime_simulator.get_service_alerts(active_only=True)
        
        categories = {
            "critical": [],
            "high": [],
            "moderate": [],
            "low": []
        }
        
        for alert in alerts:
            if alert.severity == DisruptionSeverity.CRITICAL:
                categories["critical"].append(alert)
            elif alert.severity == DisruptionSeverity.HIGH:
                categories["high"].append(alert)
            elif alert.severity == DisruptionSeverity.MODERATE:
                categories["moderate"].append(alert)
            else:
                categories["low"].append(alert)
        
        return categories
    
    def get_system_wide_status(self) -> Dict[str, any]:
        """Get overall system status"""
        
        alerts = realtime_simulator.get_service_alerts(active_only=True)
        categorized_alerts = self.categorize_alerts_by_impact()
        
        # Determine overall system status
        if categorized_alerts["critical"]:
            overall_status = ServiceStatus.SUSPENDED
        elif categorized_alerts["high"]:
            overall_status = ServiceStatus.DISRUPTED  
        elif categorized_alerts["moderate"]:
            overall_status = ServiceStatus.DELAYED
        else:
            overall_status = ServiceStatus.NORMAL
        
        # Get line-specific statuses
        line_statuses = {}
        for line_id in [1, 2, 3, 4]:  # Bangkok train lines
            line_status = self.get_service_status(line_id=line_id)
            line_statuses[line_id] = line_status
        
        return {
            "overall_status": overall_status,
            "total_alerts": len(alerts),
            "alert_breakdown": {k: len(v) for k, v in categorized_alerts.items()},
            "line_statuses": line_statuses,
            "active_maintenance": len(self.get_maintenance_windows(active_only=True)),
            "last_updated": datetime.now()
        }
    
    def add_notification_callback(self, callback: callable):
        """Add callback for status notifications"""
        self._notification_callbacks.append(callback)
    
    def _trigger_alert_notifications(self, alert: ServiceAlert, is_update: bool = False):
        """Trigger notifications for service alerts"""
        
        notification_type = "alert_update" if is_update else "new_alert"
        
        for callback in self._notification_callbacks:
            try:
                callback({
                    "type": notification_type,
                    "alert": alert,
                    "timestamp": datetime.now()
                })
            except Exception as e:
                print(f"Error triggering alert notification: {e}")
    
    def _trigger_resolution_notifications(self, alert: ServiceAlert):
        """Trigger notifications for alert resolutions"""
        
        for callback in self._notification_callbacks:
            try:
                callback({
                    "type": "alert_resolved",
                    "alert": alert,
                    "timestamp": datetime.now()
                })
            except Exception as e:
                print(f"Error triggering resolution notification: {e}")
    
    def _generate_status_description(
        self, 
        status: ServiceStatus, 
        alerts: List[ServiceAlert]
    ) -> str:
        """Generate human-readable status description"""
        
        if status == ServiceStatus.NORMAL:
            return "Service is operating normally"
        
        if not alerts:
            return f"Service status: {status.value}"
        
        # Use the most severe alert for description
        primary_alert = max(alerts, key=lambda a: list(DisruptionSeverity).index(a.severity))
        
        base_description = f"{primary_alert.title}: {primary_alert.description}"
        
        if len(alerts) > 1:
            base_description += f" (and {len(alerts) - 1} other alert{'s' if len(alerts) > 2 else ''})"
        
        return base_description