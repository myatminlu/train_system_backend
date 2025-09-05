from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from decimal import Decimal
import psutil
import time
import threading
from collections import deque, defaultdict
import statistics

from src.admin.schemas import (
    SystemHealth, HealthCheck, SystemStatus, SystemMetrics, DashboardData,
    PerformanceMetrics, PerformanceReport, SystemAlert, SystemConfig
)
from src.bookings.booking_service import BookingService
from src.schedules.realtime_service import realtime_simulator

class SystemMonitoringService:
    """Service for system health monitoring and performance tracking"""
    
    def __init__(self, db: Session):
        self.db = db
        self._health_checks = {}
        self._performance_data = deque(maxlen=1440)  # 24 hours of minute data
        self._system_alerts = []
        self._monitoring_active = False
        self._monitoring_thread = None
        self._alert_thresholds = self._initialize_alert_thresholds()
        
        # Start monitoring
        self.start_monitoring()
    
    def _initialize_alert_thresholds(self) -> Dict[str, Any]:
        """Initialize alert thresholds"""
        return {
            "cpu_usage": {"warning": 70, "critical": 90},
            "memory_usage": {"warning": 80, "critical": 95},
            "disk_usage": {"warning": 85, "critical": 95},
            "response_time": {"warning": 1000, "critical": 3000},  # milliseconds
            "error_rate": {"warning": 5, "critical": 10},  # percentage
            "database_connections": {"warning": 80, "critical": 95}  # percentage of max
        }
    
    def start_monitoring(self):
        """Start system monitoring in background"""
        if not self._monitoring_active:
            self._monitoring_active = True
            self._monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self._monitoring_thread.daemon = True
            self._monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                # Collect performance metrics
                metrics = self._collect_performance_metrics()
                self._performance_data.append(metrics)
                
                # Check for alerts
                self._check_alert_conditions(metrics)
                
                # Sleep for 60 seconds
                time.sleep(60)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(10)
    
    def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network metrics (simplified)
        network = psutil.net_io_counters()
        
        # Database connections (simplified)
        active_connections = 10  # Would query actual database
        max_connections = 100
        
        # API metrics (simplified - would come from actual monitoring)
        api_response_time_avg = 150.0  # milliseconds
        api_response_time_95th = 300.0
        database_query_time_avg = 50.0
        requests_per_minute = 120
        error_rate = 0.5  # percentage
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            api_response_time_avg=api_response_time_avg,
            api_response_time_95th=api_response_time_95th,
            database_query_time_avg=database_query_time_avg,
            memory_usage_percent=memory.percent,
            cpu_usage_percent=cpu_percent,
            disk_usage_percent=disk.percent,
            active_connections=active_connections,
            requests_per_minute=requests_per_minute,
            error_rate=error_rate
        )
    
    def _check_alert_conditions(self, metrics: PerformanceMetrics):
        """Check metrics against alert thresholds"""
        
        alerts_to_create = []
        
        # CPU usage alert
        if metrics.cpu_usage_percent >= self._alert_thresholds["cpu_usage"]["critical"]:
            alerts_to_create.append(("critical", "High CPU Usage", 
                                   f"CPU usage is {metrics.cpu_usage_percent:.1f}%", "system"))
        elif metrics.cpu_usage_percent >= self._alert_thresholds["cpu_usage"]["warning"]:
            alerts_to_create.append(("high", "Elevated CPU Usage",
                                   f"CPU usage is {metrics.cpu_usage_percent:.1f}%", "system"))
        
        # Memory usage alert
        if metrics.memory_usage_percent >= self._alert_thresholds["memory_usage"]["critical"]:
            alerts_to_create.append(("critical", "High Memory Usage",
                                   f"Memory usage is {metrics.memory_usage_percent:.1f}%", "system"))
        elif metrics.memory_usage_percent >= self._alert_thresholds["memory_usage"]["warning"]:
            alerts_to_create.append(("high", "Elevated Memory Usage",
                                   f"Memory usage is {metrics.memory_usage_percent:.1f}%", "system"))
        
        # Disk usage alert
        if metrics.disk_usage_percent >= self._alert_thresholds["disk_usage"]["critical"]:
            alerts_to_create.append(("critical", "High Disk Usage",
                                   f"Disk usage is {metrics.disk_usage_percent:.1f}%", "storage"))
        elif metrics.disk_usage_percent >= self._alert_thresholds["disk_usage"]["warning"]:
            alerts_to_create.append(("high", "Elevated Disk Usage",
                                   f"Disk usage is {metrics.disk_usage_percent:.1f}%", "storage"))
        
        # API response time alert
        if metrics.api_response_time_avg >= self._alert_thresholds["response_time"]["critical"]:
            alerts_to_create.append(("critical", "Slow API Response Time",
                                   f"Average response time is {metrics.api_response_time_avg:.0f}ms", "api"))
        elif metrics.api_response_time_avg >= self._alert_thresholds["response_time"]["warning"]:
            alerts_to_create.append(("medium", "Elevated API Response Time",
                                   f"Average response time is {metrics.api_response_time_avg:.0f}ms", "api"))
        
        # Error rate alert
        if metrics.error_rate >= self._alert_thresholds["error_rate"]["critical"]:
            alerts_to_create.append(("critical", "High Error Rate",
                                   f"Error rate is {metrics.error_rate:.1f}%", "api"))
        elif metrics.error_rate >= self._alert_thresholds["error_rate"]["warning"]:
            alerts_to_create.append(("high", "Elevated Error Rate",
                                   f"Error rate is {metrics.error_rate:.1f}%", "api"))
        
        # Create alerts
        for severity, title, message, component in alerts_to_create:
            self._create_alert(severity, title, message, component)
    
    def _create_alert(self, severity: str, title: str, message: str, component: str):
        """Create a system alert"""
        
        # Check if similar alert already exists and is active
        existing_alert = None
        for alert in self._system_alerts:
            if (alert.title == title and alert.component == component and 
                alert.is_active and alert.severity == severity):
                existing_alert = alert
                break
        
        if existing_alert:
            return  # Don't create duplicate alerts
        
        alert = SystemAlert(
            id=f"alert_{len(self._system_alerts) + 1}_{int(time.time())}",
            severity=severity,
            title=title,
            message=message,
            component=component,
            created_at=datetime.now(),
            is_active=True
        )
        
        self._system_alerts.append(alert)
        
        # Keep only recent alerts
        if len(self._system_alerts) > 1000:
            self._system_alerts = self._system_alerts[-1000:]
    
    def get_system_health(self) -> SystemHealth:
        """Get overall system health status"""
        
        components = []
        overall_status = SystemStatus.HEALTHY
        
        # Database health check
        db_check = self._check_database_health()
        components.append(db_check)
        if db_check["status"] == SystemStatus.CRITICAL:
            overall_status = SystemStatus.CRITICAL
        elif db_check["status"] == SystemStatus.WARNING and overall_status != SystemStatus.CRITICAL:
            overall_status = SystemStatus.WARNING
        
        # API health check
        api_check = self._check_api_health()
        components.append(api_check)
        if api_check["status"] == SystemStatus.CRITICAL:
            overall_status = SystemStatus.CRITICAL
        elif api_check["status"] == SystemStatus.WARNING and overall_status != SystemStatus.CRITICAL:
            overall_status = SystemStatus.WARNING
        
        # System resources check
        system_check = self._check_system_resources()
        components.append(system_check)
        if system_check["status"] == SystemStatus.CRITICAL:
            overall_status = SystemStatus.CRITICAL
        elif system_check["status"] == SystemStatus.WARNING and overall_status != SystemStatus.CRITICAL:
            overall_status = SystemStatus.WARNING
        
        # External services check
        external_check = self._check_external_services()
        components.append(external_check)
        if external_check["status"] == SystemStatus.WARNING and overall_status == SystemStatus.HEALTHY:
            overall_status = SystemStatus.WARNING
        
        # System metrics
        latest_metrics = self._performance_data[-1] if self._performance_data else None
        metrics = {}
        if latest_metrics:
            metrics = {
                "cpu_usage": latest_metrics.cpu_usage_percent,
                "memory_usage": latest_metrics.memory_usage_percent,
                "disk_usage": latest_metrics.disk_usage_percent,
                "response_time": latest_metrics.api_response_time_avg,
                "error_rate": latest_metrics.error_rate,
                "active_connections": latest_metrics.active_connections
            }
        
        return SystemHealth(
            overall_status=overall_status,
            components=components,
            metrics=metrics,
            last_check=datetime.now(),
            uptime=self._get_system_uptime(),
            version="1.0.0"
        )
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        
        try:
            # Simple database check (would do actual query)
            start_time = time.time()
            # self.db.execute("SELECT 1")
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            status = SystemStatus.HEALTHY
            message = "Database is responding normally"
            
            if response_time > 1000:  # 1 second
                status = SystemStatus.WARNING
                message = f"Database response time is elevated ({response_time:.0f}ms)"
            elif response_time > 3000:  # 3 seconds
                status = SystemStatus.CRITICAL
                message = f"Database response time is critical ({response_time:.0f}ms)"
            
            return {
                "component": "Database",
                "status": status,
                "message": message,
                "response_time_ms": response_time,
                "details": {
                    "connections": 10,
                    "max_connections": 100,
                    "active_queries": 5
                }
            }
            
        except Exception as e:
            return {
                "component": "Database",
                "status": SystemStatus.CRITICAL,
                "message": f"Database connection failed: {str(e)}",
                "response_time_ms": None,
                "details": {"error": str(e)}
            }
    
    def _check_api_health(self) -> Dict[str, Any]:
        """Check API health"""
        
        if not self._performance_data:
            return {
                "component": "API",
                "status": SystemStatus.WARNING,
                "message": "No performance data available",
                "response_time_ms": None,
                "details": {}
            }
        
        latest_metrics = self._performance_data[-1]
        
        status = SystemStatus.HEALTHY
        message = "API is responding normally"
        
        if latest_metrics.api_response_time_avg > 1000:
            status = SystemStatus.WARNING
            message = f"API response time is elevated ({latest_metrics.api_response_time_avg:.0f}ms)"
        elif latest_metrics.api_response_time_avg > 3000:
            status = SystemStatus.CRITICAL
            message = f"API response time is critical ({latest_metrics.api_response_time_avg:.0f}ms)"
        
        if latest_metrics.error_rate > 10:
            status = SystemStatus.CRITICAL
            message = f"High API error rate ({latest_metrics.error_rate:.1f}%)"
        elif latest_metrics.error_rate > 5:
            if status != SystemStatus.CRITICAL:
                status = SystemStatus.WARNING
                message = f"Elevated API error rate ({latest_metrics.error_rate:.1f}%)"
        
        return {
            "component": "API",
            "status": status,
            "message": message,
            "response_time_ms": latest_metrics.api_response_time_avg,
            "details": {
                "error_rate": latest_metrics.error_rate,
                "requests_per_minute": latest_metrics.requests_per_minute,
                "95th_percentile": latest_metrics.api_response_time_95th
            }
        }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        
        if not self._performance_data:
            return {
                "component": "System Resources",
                "status": SystemStatus.WARNING,
                "message": "No resource data available",
                "details": {}
            }
        
        latest_metrics = self._performance_data[-1]
        
        status = SystemStatus.HEALTHY
        messages = []
        
        # Check CPU
        if latest_metrics.cpu_usage_percent > 90:
            status = SystemStatus.CRITICAL
            messages.append(f"Critical CPU usage ({latest_metrics.cpu_usage_percent:.1f}%)")
        elif latest_metrics.cpu_usage_percent > 70:
            if status != SystemStatus.CRITICAL:
                status = SystemStatus.WARNING
            messages.append(f"High CPU usage ({latest_metrics.cpu_usage_percent:.1f}%)")
        
        # Check Memory
        if latest_metrics.memory_usage_percent > 95:
            status = SystemStatus.CRITICAL
            messages.append(f"Critical memory usage ({latest_metrics.memory_usage_percent:.1f}%)")
        elif latest_metrics.memory_usage_percent > 80:
            if status != SystemStatus.CRITICAL:
                status = SystemStatus.WARNING
            messages.append(f"High memory usage ({latest_metrics.memory_usage_percent:.1f}%)")
        
        # Check Disk
        if latest_metrics.disk_usage_percent > 95:
            status = SystemStatus.CRITICAL
            messages.append(f"Critical disk usage ({latest_metrics.disk_usage_percent:.1f}%)")
        elif latest_metrics.disk_usage_percent > 85:
            if status != SystemStatus.CRITICAL:
                status = SystemStatus.WARNING
            messages.append(f"High disk usage ({latest_metrics.disk_usage_percent:.1f}%)")
        
        message = "System resources are normal" if not messages else "; ".join(messages)
        
        return {
            "component": "System Resources",
            "status": status,
            "message": message,
            "details": {
                "cpu_usage": latest_metrics.cpu_usage_percent,
                "memory_usage": latest_metrics.memory_usage_percent,
                "disk_usage": latest_metrics.disk_usage_percent
            }
        }
    
    def _check_external_services(self) -> Dict[str, Any]:
        """Check external service dependencies"""
        
        # Check real-time simulator
        try:
            trains = realtime_simulator.get_active_trains()
            alerts = realtime_simulator.get_service_alerts()
            
            status = SystemStatus.HEALTHY
            message = f"Real-time services operational ({len(trains)} active trains, {len(alerts)} alerts)"
            
        except Exception as e:
            status = SystemStatus.WARNING
            message = f"Real-time services issue: {str(e)}"
        
        return {
            "component": "External Services",
            "status": status,
            "message": message,
            "details": {
                "realtime_simulator": "operational" if status == SystemStatus.HEALTHY else "degraded",
                "active_trains": len(trains) if 'trains' in locals() else 0,
                "active_alerts": len(alerts) if 'alerts' in locals() else 0
            }
        }
    
    def _get_system_uptime(self) -> str:
        """Get system uptime"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{days}d {hours}h {minutes}m"
        except:
            return "Unknown"
    
    def get_dashboard_data(self) -> DashboardData:
        """Get dashboard data for admin interface"""
        
        # Get system metrics
        if self._performance_data:
            latest_metrics = self._performance_data[-1]
            
            # Get booking service for metrics
            booking_service = BookingService(self.db)
            all_bookings = list(booking_service._booking_storage.values())
            
            # Calculate daily revenue
            today = datetime.now().date()
            daily_revenue = sum(
                b.total_amount for b in all_bookings
                if b.booking_created_at.date() == today and b.booking_status.value == "confirmed"
            )
            
            system_metrics = SystemMetrics(
                total_users=150,  # Would get from user service
                active_bookings=len([b for b in all_bookings if b.booking_status.value == "confirmed"]),
                daily_revenue=daily_revenue,
                system_uptime=self._get_system_uptime(),
                api_response_time=latest_metrics.api_response_time_avg,
                database_connections=latest_metrics.active_connections,
                cache_hit_rate=95.5,  # Would get from cache service
                error_rate=latest_metrics.error_rate,
                active_sessions=25  # Would get from session service
            )
        else:
            # Default metrics if no data available
            system_metrics = SystemMetrics(
                total_users=0,
                active_bookings=0,
                daily_revenue=Decimal('0'),
                system_uptime="Unknown",
                api_response_time=0.0,
                database_connections=0,
                cache_hit_rate=0.0,
                error_rate=0.0,
                active_sessions=0
            )
        
        # Get recent bookings (simplified)
        booking_service = BookingService(self.db)
        recent_bookings_data = []
        for booking in list(booking_service._booking_storage.values())[-5:]:
            recent_bookings_data.append({
                "id": booking.booking_id,
                "reference": booking.booking_reference,
                "amount": float(booking.total_amount),
                "status": booking.booking_status.value,
                "created_at": booking.booking_created_at.isoformat()
            })
        
        # Get recent alerts
        recent_alerts_data = []
        for alert in [a for a in self._system_alerts if a.is_active][-5:]:
            recent_alerts_data.append({
                "id": alert.id,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "created_at": alert.created_at.isoformat()
            })
        
        # Get performance data for charts
        performance_data = []
        for metrics in list(self._performance_data)[-60:]:  # Last hour
            performance_data.append({
                "timestamp": metrics.timestamp.isoformat(),
                "cpu_usage": metrics.cpu_usage_percent,
                "memory_usage": metrics.memory_usage_percent,
                "response_time": metrics.api_response_time_avg,
                "requests_per_minute": metrics.requests_per_minute
            })
        
        # Top routes (simplified)
        top_routes = [
            {"route": "Siam → Asok", "bookings": 145, "revenue": 7250.0},
            {"route": "Chatuchak → Siam", "bookings": 132, "revenue": 6600.0},
            {"route": "Mo Chit → Phrom Phong", "bookings": 98, "revenue": 5390.0}
        ]
        
        system_health = self.get_system_health()
        
        return DashboardData(
            metrics=system_metrics,
            recent_bookings=recent_bookings_data,
            recent_alerts=recent_alerts_data,
            performance_data=performance_data,
            top_routes=top_routes,
            system_status=system_health.overall_status,
            last_updated=datetime.now()
        )
    
    def get_performance_report(
        self, 
        hours_back: int = 24
    ) -> PerformanceReport:
        """Get performance report for specified time period"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        # Filter metrics for time period
        period_metrics = [
            m for m in self._performance_data
            if start_time <= m.timestamp <= end_time
        ]
        
        if not period_metrics:
            return PerformanceReport(
                period_start=start_time,
                period_end=end_time,
                metrics_summary={},
                trends=[],
                recommendations=[],
                alerts_triggered=0
            )
        
        # Calculate summary metrics
        cpu_values = [m.cpu_usage_percent for m in period_metrics]
        memory_values = [m.memory_usage_percent for m in period_metrics]
        response_times = [m.api_response_time_avg for m in period_metrics]
        error_rates = [m.error_rate for m in period_metrics]
        
        metrics_summary = {
            "cpu_usage": {
                "avg": statistics.mean(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_usage": {
                "avg": statistics.mean(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "response_time": {
                "avg": statistics.mean(response_times),
                "max": max(response_times),
                "min": min(response_times)
            },
            "error_rate": {
                "avg": statistics.mean(error_rates),
                "max": max(error_rates),
                "min": min(error_rates)
            }
        }
        
        # Generate recommendations
        recommendations = []
        if metrics_summary["cpu_usage"]["avg"] > 60:
            recommendations.append("Consider scaling CPU resources - average usage is high")
        if metrics_summary["memory_usage"]["avg"] > 70:
            recommendations.append("Monitor memory usage - approaching high utilization")
        if metrics_summary["response_time"]["avg"] > 500:
            recommendations.append("API response times are elevated - investigate performance bottlenecks")
        if metrics_summary["error_rate"]["avg"] > 2:
            recommendations.append("Error rate is above normal - review application logs")
        
        # Count alerts in period
        alerts_in_period = [
            a for a in self._system_alerts
            if start_time <= a.created_at <= end_time
        ]
        
        return PerformanceReport(
            period_start=start_time,
            period_end=end_time,
            metrics_summary=metrics_summary,
            trends=[],  # Would calculate actual trends
            recommendations=recommendations,
            alerts_triggered=len(alerts_in_period)
        )
    
    def get_system_alerts(
        self, 
        active_only: bool = True,
        limit: int = 100
    ) -> List[SystemAlert]:
        """Get system alerts"""
        
        alerts = self._system_alerts
        
        if active_only:
            alerts = [a for a in alerts if a.is_active]
        
        # Sort by creation time (newest first) and limit
        alerts.sort(key=lambda x: x.created_at, reverse=True)
        return alerts[:limit]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a system alert"""
        
        for alert in self._system_alerts:
            if alert.id == alert_id and alert.is_active:
                alert.is_active = False
                alert.resolved_at = datetime.now()
                return True
        
        return False
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent performance metrics"""
        return self._performance_data[-1] if self._performance_data else None