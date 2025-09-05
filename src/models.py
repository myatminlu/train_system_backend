from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Date, Time, Text, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base

# ================================
# Users & Roles
# ================================
class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user_roles = relationship("UserHasRole", back_populates="user")
    journeys = relationship("Journey", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user_roles = relationship("UserHasRole", back_populates="role")

class UserHasRole(Base):
    __tablename__ = "user_has_roles"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    role_id = Column(BigInteger, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")

# ================================
# Passenger Categories
# ================================
class PassengerType(Base):
    __tablename__ = "passenger_types"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    discount_percentage = Column(Numeric(5, 2), default=0.00)
    age_min = Column(Integer)
    age_max = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    fare_rules = relationship("FareRule", back_populates="passenger_type")
    tickets = relationship("Ticket", back_populates="passenger_type")

# ================================
# Regions / Systems / Stations
# ================================
class Region(Base):
    __tablename__ = "regions"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    train_companies = relationship("TrainCompany", back_populates="region")

class TrainCompany(Base):
    __tablename__ = "train_companies"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50))
    region_id = Column(BigInteger, ForeignKey("regions.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    region = relationship("Region", back_populates="train_companies")
    train_lines = relationship("TrainLine", back_populates="company")

class TrainLine(Base):
    __tablename__ = "train_lines"
    
    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("train_companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    color = Column(String(20))
    status = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("TrainCompany", back_populates="train_lines")
    stations = relationship("Station", back_populates="line")
    distance_zones = relationship("DistanceZone", back_populates="line")
    train_services = relationship("TrainService", back_populates="line")
    service_statuses = relationship("ServiceStatus", back_populates="line")

class Station(Base):
    __tablename__ = "stations"
    
    id = Column(BigInteger, primary_key=True, index=True)
    line_id = Column(BigInteger, ForeignKey("train_lines.id"))
    name = Column(String(255), nullable=False, index=True)
    lat = Column(Numeric(10, 6))
    long = Column(Numeric(10, 6))
    zone_number = Column(Integer)
    is_interchange = Column(Boolean, default=False, index=True)
    platform_count = Column(Integer, default=1)
    status = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    line = relationship("TrainLine", back_populates="stations")
    facilities = relationship("StationFacility", back_populates="station")
    routes_from = relationship("Route", foreign_keys="Route.from_station", back_populates="from_station_ref")
    routes_to = relationship("Route", foreign_keys="Route.to_station", back_populates="to_station_ref")
    transfer_points_a = relationship("TransferPoint", foreign_keys="TransferPoint.station_a_id", back_populates="station_a")
    transfer_points_b = relationship("TransferPoint", foreign_keys="TransferPoint.station_b_id", back_populates="station_b")
    service_statuses = relationship("ServiceStatus", back_populates="station")
    ticket_routes_depart = relationship("TicketRoute", foreign_keys="TicketRoute.depart_station_id", back_populates="depart_station")
    ticket_routes_arrive = relationship("TicketRoute", foreign_keys="TicketRoute.arrive_station_id", back_populates="arrive_station")

# ================================
# Distance Zones for Fare Calculation
# ================================
class DistanceZone(Base):
    __tablename__ = "distance_zones"
    
    id = Column(BigInteger, primary_key=True, index=True)
    line_id = Column(BigInteger, ForeignKey("train_lines.id"), nullable=False)
    zone_number = Column(Integer, nullable=False)
    base_fare = Column(Numeric(10, 2), nullable=False)
    per_station_fare = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    line = relationship("TrainLine", back_populates="distance_zones")

# ================================
# Transfer Points (Interchange Stations)
# ================================
class TransferPoint(Base):
    __tablename__ = "transfer_points"
    
    id = Column(BigInteger, primary_key=True, index=True)
    station_a_id = Column(BigInteger, ForeignKey("stations.id"), nullable=False, index=True)
    station_b_id = Column(BigInteger, ForeignKey("stations.id"), nullable=False, index=True)
    walking_time_minutes = Column(Integer, default=5)
    walking_distance_meters = Column(Integer)
    transfer_fee = Column(Numeric(10, 2), default=0.00)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    station_a = relationship("Station", foreign_keys=[station_a_id], back_populates="transfer_points_a")
    station_b = relationship("Station", foreign_keys=[station_b_id], back_populates="transfer_points_b")

# ================================
# Station Facilities
# ================================
class StationFacility(Base):
    __tablename__ = "station_facilities"
    
    id = Column(BigInteger, primary_key=True, index=True)
    station_id = Column(BigInteger, ForeignKey("stations.id"), nullable=False)
    facility_type = Column(String(50), nullable=False)
    is_available = Column(Boolean, default=True)
    location_description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    station = relationship("Station", back_populates="facilities")

# ================================
# Train Services & Schedules
# ================================
class TrainService(Base):
    __tablename__ = "train_services"
    
    id = Column(BigInteger, primary_key=True, index=True)
    line_id = Column(BigInteger, ForeignKey("train_lines.id"), nullable=False)
    service_name = Column(String(100))
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    frequency_minutes = Column(Integer, nullable=False)
    direction = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    line = relationship("TrainLine", back_populates="train_services")

# ================================
# Service Status (Delays, Maintenance)
# ================================
class ServiceStatus(Base):
    __tablename__ = "service_status"
    
    id = Column(BigInteger, primary_key=True, index=True)
    line_id = Column(BigInteger, ForeignKey("train_lines.id"), index=True)
    station_id = Column(BigInteger, ForeignKey("stations.id"), index=True)
    status_type = Column(String(50), nullable=False)
    severity = Column(String(20), default='low')
    message = Column(Text, nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    line = relationship("TrainLine", back_populates="service_statuses")
    station = relationship("Station", back_populates="service_statuses")

# ================================
# Routes & Fare Rules
# ================================
class Route(Base):
    __tablename__ = "routes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    from_station = Column(BigInteger, ForeignKey("stations.id"), nullable=False, index=True)
    to_station = Column(BigInteger, ForeignKey("stations.id"), nullable=False, index=True)
    transport_type = Column(String(50), nullable=False)
    duration_minutes = Column(Integer)
    distance_km = Column(Numeric(8, 2))
    avg_travel_time_minutes = Column(Integer)
    service_frequency_minutes = Column(Integer)
    base_cost = Column(Numeric(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    from_station_ref = relationship("Station", foreign_keys=[from_station], back_populates="routes_from")
    to_station_ref = relationship("Station", foreign_keys=[to_station], back_populates="routes_to")
    fare_rules = relationship("FareRule", back_populates="route")
    journey_segments = relationship("JourneySegment", back_populates="route")
    ticket_routes = relationship("TicketRoute", back_populates="route")

class FareRule(Base):
    __tablename__ = "fare_rules"
    
    id = Column(BigInteger, primary_key=True, index=True)
    route_id = Column(BigInteger, ForeignKey("routes.id"), nullable=False)
    passenger_type_id = Column(BigInteger, ForeignKey("passenger_types.id"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    valid_from = Column(Date, server_default=func.current_date())
    valid_to = Column(Date)
    
    # Relationships
    route = relationship("Route", back_populates="fare_rules")
    passenger_type = relationship("PassengerType", back_populates="fare_rules")

# ================================
# Journey (planned trips, not tickets)
# ================================
class Journey(Base):
    __tablename__ = "journeys"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    total_cost = Column(Numeric(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="journeys")
    journey_segments = relationship("JourneySegment", back_populates="journey")
    tickets = relationship("Ticket", back_populates="journey")

class JourneySegment(Base):
    __tablename__ = "journey_segments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    journey_id = Column(BigInteger, ForeignKey("journeys.id"), nullable=False)
    route_id = Column(BigInteger, ForeignKey("routes.id"), nullable=False)
    segment_order = Column(Integer, nullable=False)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    journey = relationship("Journey", back_populates="journey_segments")
    route = relationship("Route", back_populates="journey_segments")

# ================================
# Tickets & Bookings
# ================================
class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(BigInteger, primary_key=True, index=True)
    ticket_unique_string = Column(String(100), unique=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    journey_id = Column(BigInteger, ForeignKey("journeys.id"))
    passenger_type_id = Column(BigInteger, ForeignKey("passenger_types.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), default='reserved', index=True)
    valid_from = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    valid_until = Column(DateTime(timezone=True), index=True)
    qr_code_data = Column(Text)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    issued_by = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="tickets")
    journey = relationship("Journey", back_populates="tickets")
    passenger_type = relationship("PassengerType", back_populates="tickets")
    ticket_routes = relationship("TicketRoute", back_populates="ticket")

class TicketRoute(Base):
    __tablename__ = "ticket_routes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    ticket_id = Column(BigInteger, ForeignKey("tickets.id"), nullable=False, index=True)
    route_id = Column(BigInteger, ForeignKey("routes.id"), nullable=False)
    depart_station_id = Column(BigInteger, ForeignKey("stations.id"), nullable=False)
    arrive_station_id = Column(BigInteger, ForeignKey("stations.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="ticket_routes")
    route = relationship("Route", back_populates="ticket_routes")
    depart_station = relationship("Station", foreign_keys=[depart_station_id], back_populates="ticket_routes_depart")
    arrive_station = relationship("Station", foreign_keys=[arrive_station_id], back_populates="ticket_routes_arrive")

# ================================
# Admin System Models
# ================================
class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    is_2fa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String(32))
    last_login = Column(DateTime(timezone=True))
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(BigInteger, ForeignKey("admin_users.id"))
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="admin_user")
    notifications = relationship("AdminNotification", back_populates="admin_user")
    created_sessions = relationship("AdminSession", back_populates="admin_user")

class AdminSession(Base):
    __tablename__ = "admin_sessions"
    
    id = Column(String(128), primary_key=True)
    admin_user_id = Column(BigInteger, ForeignKey("admin_users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    admin_user = relationship("AdminUser", back_populates="created_sessions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    admin_user_id = Column(BigInteger, ForeignKey("admin_users.id"), index=True)
    admin_username = Column(String(50))
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(50))
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    admin_user = relationship("AdminUser", back_populates="audit_logs")

class SystemConfig(Base):
    __tablename__ = "system_configs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON)
    description = Column(Text)
    category = Column(String(50), nullable=False, index=True)
    is_sensitive = Column(Boolean, default=False)
    requires_restart = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger, ForeignKey("admin_users.id"))

class SystemAlert(Base):
    __tablename__ = "system_alerts"
    
    id = Column(String(36), primary_key=True)
    severity = Column(String(20), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    component = Column(String(50), nullable=False, index=True)
    alert_metadata = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(BigInteger, ForeignKey("admin_users.id"))

class AdminNotification(Base):
    __tablename__ = "admin_notifications"
    
    id = Column(String(36), primary_key=True)
    admin_user_id = Column(BigInteger, ForeignKey("admin_users.id"), index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(20), nullable=False, index=True)
    priority = Column(String(20), default='medium', index=True)
    notification_metadata = Column(JSON, default=dict)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    read_at = Column(DateTime(timezone=True))
    
    # Relationships
    admin_user = relationship("AdminUser", back_populates="notifications")

class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    
    id = Column(BigInteger, primary_key=True, index=True)
    admin_user_id = Column(BigInteger, ForeignKey("admin_users.id"), unique=True, nullable=False)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    system_alerts = Column(Boolean, default=True)
    booking_alerts = Column(Boolean, default=True)
    performance_alerts = Column(Boolean, default=True)
    security_alerts = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class BackupLog(Base):
    __tablename__ = "backup_logs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    backup_id = Column(String(50), unique=True, nullable=False)
    backup_type = Column(String(50), default='full')
    file_path = Column(String(500))
    file_size_bytes = Column(BigInteger)
    status = Column(String(20), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    triggered_by = Column(BigInteger, ForeignKey("admin_users.id"))

class MaintenanceWindow(Base):
    __tablename__ = "maintenance_windows"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    maintenance_type = Column(String(50), nullable=False, index=True)
    affected_services = Column(JSON, default=list)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    notification_sent = Column(Boolean, default=False)
    status = Column(String(20), default='scheduled', index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(BigInteger, ForeignKey("admin_users.id"))

class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(BigInteger, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    api_response_time_avg = Column(Numeric(8, 4))
    api_response_time_95th = Column(Numeric(8, 4))
    database_query_time_avg = Column(Numeric(8, 4))
    memory_usage_percent = Column(Numeric(5, 2))
    cpu_usage_percent = Column(Numeric(5, 2))
    disk_usage_percent = Column(Numeric(5, 2))
    active_connections = Column(Integer)
    requests_per_minute = Column(Integer)
    error_rate = Column(Numeric(5, 4))
    additional_metrics = Column(JSON, default=dict)