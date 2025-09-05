from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from decimal import Decimal
import json
import csv
import io
from collections import defaultdict

from src.admin.schemas import (
    AdminStationCreate, AdminStationUpdate, AdminStationBulkOperation,
    UserAnalytics, SystemConfig, SystemConfigUpdate, BookingAnalyticsRequest,
    BookingAnalyticsResponse, RoutePopularityAnalytics, RevenueReport,
    DataExportRequest, DataExportResponse, BulkOperationResult,
    AdminNotification, NotificationSettings
)
from src.models import Station, TrainLine, User
from src.bookings.booking_service import BookingService
# AdminAuthService removed per user request

class AdminManagementService:
    """Service for administrative management operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.booking_service = BookingService(db)
        self._system_configs = self._initialize_system_configs()
        self._notifications = []
        self._export_files = {}
        
    def _initialize_system_configs(self) -> Dict[str, SystemConfig]:
        """Initialize system configuration settings"""
        
        configs = {
            "booking_expiry_minutes": SystemConfig(
                key="booking_expiry_minutes",
                value=30,
                description="Minutes before unconfirmed bookings expire",
                category="booking",
                requires_restart=False
            ),
            "max_advance_booking_days": SystemConfig(
                key="max_advance_booking_days",
                value=30,
                description="Maximum days in advance to allow bookings",
                category="booking",
                requires_restart=False
            ),
            "api_rate_limit_per_minute": SystemConfig(
                key="api_rate_limit_per_minute",
                value=100,
                description="API requests per minute per user",
                category="api",
                requires_restart=True
            ),
            "maintenance_mode": SystemConfig(
                key="maintenance_mode",
                value=False,
                description="Enable maintenance mode",
                category="system",
                requires_restart=False
            ),
            "email_notifications_enabled": SystemConfig(
                key="email_notifications_enabled",
                value=True,
                description="Enable email notifications",
                category="notifications",
                requires_restart=False
            ),
            "default_passenger_type_id": SystemConfig(
                key="default_passenger_type_id",
                value=1,
                description="Default passenger type for bookings",
                category="booking",
                requires_restart=False
            ),
            "max_passengers_per_booking": SystemConfig(
                key="max_passengers_per_booking",
                value=10,
                description="Maximum passengers allowed per booking",
                category="booking",
                requires_restart=False
            ),
            "system_backup_retention_days": SystemConfig(
                key="system_backup_retention_days",
                value=30,
                description="Days to retain system backups",
                category="system",
                requires_restart=False
            )
        }
        
        return configs
    
    # Station Management
    def create_station(
        self, 
        station_data: AdminStationCreate,
        created_by_id: int
    ) -> Station:
        """Create a new station"""
        
        # Validate line exists
        line = self.db.query(TrainLine).filter(TrainLine.id == station_data.line_id).first()
        if not line:
            raise ValueError(f"Train line {station_data.line_id} not found")
        
        # Check for duplicate station name on same line
        existing = self.db.query(Station).filter(
            Station.name == station_data.name,
            Station.line_id == station_data.line_id
        ).first()
        
        if existing:
            raise ValueError(f"Station '{station_data.name}' already exists on {line.name}")
        
        # Create station
        new_station = Station(
            name=station_data.name,
            lat=station_data.lat,
            long=station_data.long,
            line_id=station_data.line_id,
            zone_number=station_data.zone_number,
            platform_count=station_data.platform_count,
            is_interchange=station_data.is_interchange,
            status=station_data.status,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.db.add(new_station)
        self.db.commit()
        self.db.refresh(new_station)
        
        return new_station
    
    def update_station(
        self,
        station_id: int,
        update_data: AdminStationUpdate,
        updated_by_id: int
    ) -> Station:
        """Update an existing station"""
        
        station = self.db.query(Station).filter(Station.id == station_id).first()
        if not station:
            raise ValueError(f"Station {station_id} not found")
        
        # Update fields
        if update_data.name is not None:
            station.name = update_data.name
        
        if update_data.lat is not None:
            station.lat = update_data.lat
        
        if update_data.long is not None:
            station.long = update_data.long
        
        if update_data.line_id is not None:
            # Validate new line exists
            line = self.db.query(TrainLine).filter(TrainLine.id == update_data.line_id).first()
            if not line:
                raise ValueError(f"Train line {update_data.line_id} not found")
            station.line_id = update_data.line_id
        
        if update_data.zone_number is not None:
            station.zone_number = update_data.zone_number
        
        if update_data.platform_count is not None:
            station.platform_count = update_data.platform_count
        
        if update_data.is_interchange is not None:
            station.is_interchange = update_data.is_interchange
        
        if update_data.status is not None:
            station.status = update_data.status
        
        station.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(station)
        
        return station
    
    def delete_station(self, station_id: int, deleted_by_id: int) -> bool:
        """Delete a station"""
        
        station = self.db.query(Station).filter(Station.id == station_id).first()
        if not station:
            raise ValueError(f"Station {station_id} not found")
        
        # Check if station has bookings (would prevent deletion in real system)
        # For now, just mark as inactive
        station.status = "inactive"
        station.updated_at = datetime.now()
        
        self.db.commit()
        return True
    
    def bulk_station_operation(
        self,
        operation: AdminStationBulkOperation,
        performed_by_id: int
    ) -> BulkOperationResult:
        """Perform bulk operations on stations"""
        
        operation_id = f"bulk_{int(datetime.now().timestamp())}"
        successful_items = 0
        failed_items = 0
        errors = []
        
        for station_id in operation.station_ids:
            try:
                if operation.operation == "delete":
                    self.delete_station(station_id, performed_by_id)
                    successful_items += 1
                
                elif operation.operation == "activate":
                    station = self.db.query(Station).filter(Station.id == station_id).first()
                    if station:
                        station.status = "active"
                        station.updated_at = datetime.now()
                        self.db.commit()
                        successful_items += 1
                    else:
                        failed_items += 1
                        errors.append({"station_id": station_id, "error": "Station not found"})
                
                elif operation.operation == "deactivate":
                    station = self.db.query(Station).filter(Station.id == station_id).first()
                    if station:
                        station.status = "inactive"
                        station.updated_at = datetime.now()
                        self.db.commit()
                        successful_items += 1
                    else:
                        failed_items += 1
                        errors.append({"station_id": station_id, "error": "Station not found"})
                
                elif operation.operation == "update" and operation.update_data:
                    update_request = AdminStationUpdate(**operation.update_data)
                    self.update_station(station_id, update_request, performed_by_id)
                    successful_items += 1
                
            except Exception as e:
                failed_items += 1
                errors.append({"station_id": station_id, "error": str(e)})
        
        return BulkOperationResult(
            operation_id=operation_id,
            total_items=len(operation.station_ids),
            successful_items=successful_items,
            failed_items=failed_items,
            errors=errors,
            warnings=[],
            completed_at=datetime.now()
        )
    
    # User Management
    def get_user_analytics(self) -> UserAnalytics:
        """Get user analytics and statistics"""
        
        # In a real system, this would query the actual user database
        # For now, return simulated data
        
        total_users = 1250
        active_users = 890
        new_registrations_today = 15
        
        # Calculate growth rate (simplified)
        user_growth_rate = 5.2  # percentage
        
        top_locations = [
            {"location": "Bangkok", "users": 820, "percentage": 65.6},
            {"location": "Nonthaburi", "users": 156, "percentage": 12.5},
            {"location": "Samut Prakan", "users": 98, "percentage": 7.8},
            {"location": "Pathum Thani", "users": 76, "percentage": 6.1},
            {"location": "Other", "users": 100, "percentage": 8.0}
        ]
        
        activity_patterns = [
            {"hour": 7, "registrations": 45, "logins": 230},
            {"hour": 8, "registrations": 62, "logins": 380},
            {"hour": 9, "registrations": 38, "logins": 190},
            {"hour": 17, "registrations": 55, "logins": 420},
            {"hour": 18, "registrations": 71, "logins": 510},
            {"hour": 19, "registrations": 44, "logins": 290}
        ]
        
        return UserAnalytics(
            total_users=total_users,
            active_users=active_users,
            new_registrations_today=new_registrations_today,
            user_growth_rate=user_growth_rate,
            top_user_locations=top_locations,
            user_activity_patterns=activity_patterns
        )
    
    # System Configuration
    def get_system_configs(self, category: Optional[str] = None) -> List[SystemConfig]:
        """Get system configuration settings"""
        
        configs = list(self._system_configs.values())
        
        if category:
            configs = [c for c in configs if c.category == category]
        
        return configs
    
    def update_system_configs(
        self,
        update_request: SystemConfigUpdate,
        updated_by_id: int
    ) -> List[SystemConfig]:
        """Update system configuration settings"""
        
        updated_configs = []
        
        for config_data in update_request.configs:
            config_key = config_data.get("key")
            config_value = config_data.get("value")
            
            if config_key in self._system_configs:
                config = self._system_configs[config_key]
                old_value = config.value
                config.value = config_value
                updated_configs.append(config)
                
                # Create notification if config requires restart
                if config.requires_restart:
                    self._create_notification(
                        title="System Restart Required",
                        message=f"Configuration '{config.description}' has been updated and requires a system restart to take effect.",
                        notification_type="warning",
                        priority="high"
                    )
        
        return updated_configs
    
    # Analytics and Reporting
    def get_booking_analytics(
        self,
        request: BookingAnalyticsRequest
    ) -> BookingAnalyticsResponse:
        """Get booking analytics for specified period"""
        
        # Get bookings from booking service
        all_bookings = list(self.booking_service._booking_storage.values())
        
        # Filter bookings by date range
        start_datetime = datetime.combine(request.date_from, datetime.min.time())
        end_datetime = datetime.combine(request.date_to, datetime.max.time())
        
        filtered_bookings = [
            b for b in all_bookings
            if start_datetime <= b.booking_created_at <= end_datetime
        ]
        
        if not request.include_cancelled:
            filtered_bookings = [
                b for b in filtered_bookings
                if b.booking_status.value != "cancelled"
            ]
        
        # Calculate metrics
        total_bookings = len(filtered_bookings)
        confirmed_bookings = [b for b in filtered_bookings if b.booking_status.value == "confirmed"]
        
        total_revenue = sum(b.total_amount for b in confirmed_bookings)
        average_booking_value = total_revenue / len(confirmed_bookings) if confirmed_bookings else Decimal('0')
        
        # Calculate cancellation rate
        cancelled_bookings = [b for b in all_bookings if b.booking_status.value == "cancelled"]
        cancellation_rate = (len(cancelled_bookings) / len(all_bookings)) * 100 if all_bookings else 0
        
        # Generate trends (simplified)
        booking_trends = []
        revenue_trends = []
        
        # Group by requested time period
        if request.group_by == "day":
            # Daily trends
            current_date = request.date_from
            while current_date <= request.date_to:
                day_bookings = [
                    b for b in filtered_bookings
                    if b.booking_created_at.date() == current_date
                ]
                day_revenue = sum(
                    b.total_amount for b in day_bookings
                    if b.booking_status.value == "confirmed"
                )
                
                booking_trends.append({
                    "date": current_date.isoformat(),
                    "bookings": len(day_bookings),
                    "confirmed_bookings": len([b for b in day_bookings if b.booking_status.value == "confirmed"])
                })
                
                revenue_trends.append({
                    "date": current_date.isoformat(),
                    "revenue": float(day_revenue)
                })
                
                current_date += timedelta(days=1)
        
        # Calculate popular routes
        route_counts = defaultdict(lambda: {"count": 0, "revenue": Decimal('0')})
        for booking in confirmed_bookings:
            route_key = f"{booking.journey.from_station_id}-{booking.journey.to_station_id}"
            route_counts[route_key]["count"] += 1
            route_counts[route_key]["revenue"] += booking.total_amount
        
        popular_routes = []
        for route_key, data in sorted(route_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:5]:
            from_id, to_id = route_key.split("-")
            popular_routes.append({
                "route": route_key,
                "from_station_id": int(from_id),
                "to_station_id": int(to_id),
                "bookings": data["count"],
                "revenue": float(data["revenue"])
            })
        
        # Calculate peak booking hours
        hour_counts = defaultdict(int)
        for booking in filtered_bookings:
            hour_counts[booking.booking_created_at.hour] += 1
        
        peak_booking_hours = [
            {"hour": hour, "bookings": count}
            for hour, count in sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        return BookingAnalyticsResponse(
            total_bookings=total_bookings,
            total_revenue=total_revenue,
            average_booking_value=average_booking_value,
            booking_trends=booking_trends,
            revenue_trends=revenue_trends,
            popular_routes=popular_routes,
            peak_booking_hours=peak_booking_hours,
            cancellation_rate=cancellation_rate
        )
    
    def get_route_popularity_analytics(
        self,
        days_back: int = 30
    ) -> List[RoutePopularityAnalytics]:
        """Get route popularity analytics"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get bookings from booking service
        all_bookings = list(self.booking_service._booking_storage.values())
        
        # Filter confirmed bookings in date range
        filtered_bookings = [
            b for b in all_bookings
            if (start_date <= b.booking_created_at <= end_date and
                b.booking_status.value == "confirmed")
        ]
        
        # Analyze routes
        route_data = defaultdict(lambda: {
            "bookings": 0,
            "revenue": Decimal('0'),
            "total_time": 0,
            "from_station_name": "",
            "to_station_name": ""
        })
        
        for booking in filtered_bookings:
            route_key = f"{booking.journey.from_station_id}-{booking.journey.to_station_id}"
            data = route_data[route_key]
            
            data["bookings"] += 1
            data["revenue"] += booking.total_amount
            data["total_time"] += booking.journey.total_duration_minutes
            data["from_station_name"] = booking.journey.segments[0].from_station_name
            data["to_station_name"] = booking.journey.segments[-1].to_station_name
        
        # Convert to analytics objects
        analytics = []
        sorted_routes = sorted(route_data.items(), key=lambda x: x[1]["bookings"], reverse=True)
        
        for rank, (route_key, data) in enumerate(sorted_routes, 1):
            avg_time = data["total_time"] // data["bookings"] if data["bookings"] > 0 else 0
            
            # Calculate growth rate (simplified - would compare to previous period)
            growth_rate = 5.2 if rank <= 3 else 2.1 if rank <= 10 else -1.5
            
            analytics.append(RoutePopularityAnalytics(
                route=route_key,
                from_station_name=data["from_station_name"],
                to_station_name=data["to_station_name"],
                booking_count=data["bookings"],
                revenue=data["revenue"],
                average_journey_time=avg_time,
                popularity_rank=rank,
                growth_rate=growth_rate
            ))
        
        return analytics[:20]  # Top 20 routes
    
    def get_revenue_report(
        self,
        period: str,
        date_from: date,
        date_to: date
    ) -> RevenueReport:
        """Get revenue report for specified period"""
        
        # Get confirmed bookings in date range
        all_bookings = list(self.booking_service._booking_storage.values())
        
        start_datetime = datetime.combine(date_from, datetime.min.time())
        end_datetime = datetime.combine(date_to, datetime.max.time())
        
        confirmed_bookings = [
            b for b in all_bookings
            if (start_datetime <= b.booking_created_at <= end_datetime and
                b.booking_status.value == "confirmed")
        ]
        
        total_revenue = sum(b.total_amount for b in confirmed_bookings)
        
        # Revenue by line
        line_revenue = defaultdict(lambda: {"bookings": 0, "revenue": Decimal('0'), "line_name": ""})
        
        for booking in confirmed_bookings:
            for segment in booking.journey.segments:
                if segment.line_id and segment.transport_type == "train":
                    line_revenue[segment.line_id]["bookings"] += 1
                    line_revenue[segment.line_id]["revenue"] += segment.cost
                    line_revenue[segment.line_id]["line_name"] = segment.line_name or f"Line {segment.line_id}"
        
        revenue_by_line = [
            {
                "line_id": line_id,
                "line_name": data["line_name"],
                "bookings": data["bookings"],
                "revenue": float(data["revenue"])
            }
            for line_id, data in line_revenue.items()
        ]
        
        # Revenue by passenger type
        passenger_revenue = defaultdict(lambda: {"bookings": 0, "revenue": Decimal('0')})
        
        for booking in confirmed_bookings:
            for passenger in booking.passengers:
                pt_name = passenger.passenger_type_name
                passenger_revenue[pt_name]["bookings"] += 1
                # Simplified revenue attribution
                passenger_revenue[pt_name]["revenue"] += booking.total_amount / len(booking.passengers)
        
        revenue_by_passenger_type = [
            {
                "passenger_type": pt_name,
                "bookings": data["bookings"],
                "revenue": float(data["revenue"])
            }
            for pt_name, data in passenger_revenue.items()
        ]
        
        # Revenue trends (simplified)
        revenue_trends = []
        current_date = date_from
        while current_date <= date_to:
            day_bookings = [
                b for b in confirmed_bookings
                if b.booking_created_at.date() == current_date
            ]
            day_revenue = sum(b.total_amount for b in day_bookings)
            
            revenue_trends.append({
                "date": current_date.isoformat(),
                "revenue": float(day_revenue),
                "bookings": len(day_bookings)
            })
            
            current_date += timedelta(days=1)
        
        # Projected revenue (simplified calculation)
        if len(revenue_trends) >= 7:
            recent_avg = sum(float(t["revenue"]) for t in revenue_trends[-7:]) / 7
            projected_revenue = Decimal(str(recent_avg * 30))  # 30-day projection
        else:
            projected_revenue = None
        
        return RevenueReport(
            period=period,
            total_revenue=total_revenue,
            revenue_by_line=revenue_by_line,
            revenue_by_passenger_type=revenue_by_passenger_type,
            revenue_trends=revenue_trends,
            projected_revenue=projected_revenue
        )
    
    # Data Export
    def export_data(self, request: DataExportRequest) -> DataExportResponse:
        """Export data in requested format"""
        
        export_id = f"export_{int(datetime.now().timestamp())}"
        
        # Generate data based on type
        data = self._generate_export_data(request)
        
        # Create file content
        if request.format == "csv":
            file_content = self._generate_csv(data)
            filename = f"{request.data_type}_export.csv"
        elif request.format == "json":
            file_content = json.dumps(data, indent=2, default=str)
            filename = f"{request.data_type}_export.json"
        else:  # xlsx
            file_content = self._generate_excel(data)
            filename = f"{request.data_type}_export.xlsx"
        
        # Store file (in real system, would save to file storage)
        file_path = f"/tmp/{filename}"
        self._export_files[export_id] = {
            "content": file_content,
            "filename": filename,
            "path": file_path
        }
        
        return DataExportResponse(
            export_id=export_id,
            file_url=f"/admin/exports/{export_id}",
            file_size_bytes=len(file_content.encode() if isinstance(file_content, str) else file_content),
            record_count=len(data) if isinstance(data, list) else 1,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24)
        )
    
    def _generate_export_data(self, request: DataExportRequest) -> List[Dict[str, Any]]:
        """Generate data for export based on request type"""
        
        if request.data_type == "bookings":
            bookings = list(self.booking_service._booking_storage.values())
            
            if request.date_from:
                start_date = datetime.combine(request.date_from, datetime.min.time())
                bookings = [b for b in bookings if b.booking_created_at >= start_date]
            
            if request.date_to:
                end_date = datetime.combine(request.date_to, datetime.max.time())
                bookings = [b for b in bookings if b.booking_created_at <= end_date]
            
            return [
                {
                    "booking_id": b.booking_id,
                    "booking_reference": b.booking_reference,
                    "user_id": b.user_id,
                    "status": b.booking_status.value,
                    "total_amount": float(b.total_amount),
                    "passenger_count": len(b.passengers),
                    "from_station": b.journey.segments[0].from_station_name,
                    "to_station": b.journey.segments[-1].to_station_name,
                    "departure_time": b.journey.departure_time.isoformat(),
                    "created_at": b.booking_created_at.isoformat()
                }
                for b in bookings
            ]
        
        elif request.data_type == "stations":
            # Would query actual stations from database
            stations = self.db.query(Station).all()
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "line_id": s.line_id,
                    "lat": float(s.lat) if s.lat else None,
                    "long": float(s.long) if s.long else None,
                    "zone_number": s.zone_number,
                    "is_interchange": s.is_interchange,
                    "platform_count": s.platform_count,
                    "status": s.status,
                    "created_at": s.created_at.isoformat()
                }
                for s in stations
            ]
        
        # Add other data types as needed
        return []
    
    def _generate_csv(self, data: List[Dict[str, Any]]) -> str:
        """Generate CSV content from data"""
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    def _generate_excel(self, data: List[Dict[str, Any]]) -> bytes:
        """Generate Excel content from data (simplified)"""
        # Would use openpyxl or xlsxwriter in real implementation
        return b"Excel content placeholder"
    
    # Notifications
    def _create_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        priority: str = "medium",
        admin_user_id: Optional[int] = None
    ):
        """Create an admin notification"""
        
        notification = AdminNotification(
            id=f"notif_{int(datetime.now().timestamp())}",
            title=title,
            message=message,
            type=notification_type,
            priority=priority,
            created_at=datetime.now(),
            admin_user_id=admin_user_id
        )
        
        self._notifications.append(notification)
        
        # Keep only recent notifications
        if len(self._notifications) > 500:
            self._notifications = self._notifications[-500:]
    
    def get_notifications(
        self,
        admin_user_id: Optional[int] = None,
        unread_only: bool = False
    ) -> List[AdminNotification]:
        """Get notifications for admin user"""
        
        notifications = self._notifications
        
        # Filter by user (None = broadcast to all)
        if admin_user_id:
            notifications = [
                n for n in notifications
                if n.admin_user_id is None or n.admin_user_id == admin_user_id
            ]
        
        if unread_only:
            notifications = [n for n in notifications if n.read_at is None]
        
        # Sort by creation time (newest first)
        notifications.sort(key=lambda x: x.created_at, reverse=True)
        
        return notifications[:50]  # Limit to 50 notifications
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        
        for notification in self._notifications:
            if notification.id == notification_id:
                notification.read_at = datetime.now()
                return True
        
        return False