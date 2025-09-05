#!/usr/bin/env python3
"""
Admin Seed Data Script

Creates initial admin users and system configurations for the Bangkok Train Transport System.
This script should be run after the database migrations to set up the admin system.

Usage:
    python seed_admin_data.py
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import get_db, engine
from src.models import AdminUser, SystemConfig, PerformanceMetrics, NotificationSettings
from sqlalchemy.orm import Session
from sqlalchemy import text

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_initial_admin_users(db: Session):
    """Create initial admin users"""
    print("🔧 Creating initial admin users...")
    
    # Check if admin users already exist
    existing_admin = db.query(AdminUser).filter(AdminUser.username == "superadmin").first()
    if existing_admin:
        print("✅ Super admin user already exists, skipping...")
        return
    
    # Create super admin user
    super_admin = AdminUser(
        username="superadmin",
        email="admin@bangkoktrain.com",
        password_hash=hash_password("Admin123!"),
        full_name="System Super Administrator",
        role="super_admin",
        is_active=True,
        is_2fa_enabled=False,
        permissions=[
            "system:admin", "users:admin", "stations:admin", "analytics:admin", 
            "config:admin", "audit:admin", "export:admin", "dashboard:admin"
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(super_admin)
    
    # Create demo admin user
    demo_admin = AdminUser(
        username="admin",
        email="demo@bangkoktrain.com", 
        password_hash=hash_password("Demo123!"),
        full_name="Demo Administrator",
        role="admin",
        is_active=True,
        is_2fa_enabled=False,
        permissions=[
            "system:read", "system:write", "users:read", "users:write",
            "stations:read", "stations:write", "analytics:read", "dashboard:read"
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(demo_admin)
    
    # Create demo operator user
    demo_operator = AdminUser(
        username="operator",
        email="operator@bangkoktrain.com",
        password_hash=hash_password("Operator123!"),
        full_name="System Operator", 
        role="operator",
        is_active=True,
        is_2fa_enabled=False,
        permissions=[
            "system:read", "stations:read", "stations:write", 
            "dashboard:read", "analytics:read"
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(demo_operator)
    
    # Create demo viewer user
    demo_viewer = AdminUser(
        username="viewer",
        email="viewer@bangkoktrain.com",
        password_hash=hash_password("Viewer123!"),
        full_name="System Viewer",
        role="viewer", 
        is_active=True,
        is_2fa_enabled=False,
        permissions=[
            "system:read", "stations:read", "dashboard:read", "analytics:read"
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(demo_viewer)
    
    db.commit()
    print("✅ Created 4 initial admin users:")
    print("   - superadmin / Admin123!")
    print("   - admin / Demo123!")
    print("   - operator / Operator123!")
    print("   - viewer / Viewer123!")

def create_system_configs(db: Session):
    """Create initial system configurations"""
    print("⚙️  Creating system configurations...")
    
    # Check if configs already exist
    existing_config = db.query(SystemConfig).filter(SystemConfig.key == "system.maintenance_mode").first()
    if existing_config:
        print("✅ System configurations already exist, skipping...")
        return
    
    configs = [
        {
            "key": "system.maintenance_mode",
            "value": False,
            "description": "Enable/disable maintenance mode",
            "category": "system",
            "is_sensitive": False,
            "requires_restart": False
        },
        {
            "key": "system.max_login_attempts", 
            "value": 5,
            "description": "Maximum login attempts before account lockout",
            "category": "security",
            "is_sensitive": False,
            "requires_restart": False
        },
        {
            "key": "system.session_timeout_minutes",
            "value": 480,  # 8 hours
            "description": "Admin session timeout in minutes",
            "category": "security",
            "is_sensitive": False,
            "requires_restart": False
        },
        {
            "key": "monitoring.performance_threshold_cpu",
            "value": 80.0,
            "description": "CPU usage threshold for alerts (%)",
            "category": "monitoring",
            "is_sensitive": False,
            "requires_restart": False
        },
        {
            "key": "monitoring.performance_threshold_memory", 
            "value": 85.0,
            "description": "Memory usage threshold for alerts (%)",
            "category": "monitoring",
            "is_sensitive": False,
            "requires_restart": False
        },
        {
            "key": "monitoring.performance_threshold_disk",
            "value": 90.0,
            "description": "Disk usage threshold for alerts (%)",
            "category": "monitoring",
            "is_sensitive": False,
            "requires_restart": False
        },
        {
            "key": "backup.retention_days",
            "value": 30,
            "description": "Number of days to retain backups",
            "category": "backup",
            "is_sensitive": False,
            "requires_restart": False
        },
        {
            "key": "notifications.email_enabled",
            "value": True,
            "description": "Enable email notifications",
            "category": "notifications",
            "is_sensitive": False,
            "requires_restart": False
        }
    ]
    
    for config_data in configs:
        config = SystemConfig(
            key=config_data["key"],
            value=config_data["value"],
            description=config_data["description"],
            category=config_data["category"],
            is_sensitive=config_data["is_sensitive"],
            requires_restart=config_data["requires_restart"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(config)
    
    db.commit()
    print(f"✅ Created {len(configs)} system configurations")

def create_notification_settings(db: Session):
    """Create default notification settings for admin users"""
    print("🔔 Creating default notification settings...")
    
    admin_users = db.query(AdminUser).all()
    
    for admin_user in admin_users:
        # Check if settings already exist
        existing_settings = db.query(NotificationSettings).filter(
            NotificationSettings.admin_user_id == admin_user.id
        ).first()
        
        if not existing_settings:
            settings = NotificationSettings(
                admin_user_id=admin_user.id,
                email_enabled=True,
                push_enabled=True,
                system_alerts=True,
                booking_alerts=True,
                performance_alerts=True,
                security_alerts=True,
                updated_at=datetime.utcnow()
            )
            db.add(settings)
    
    db.commit()
    print("✅ Created default notification settings for all admin users")

def create_initial_performance_metrics(db: Session):
    """Create some initial performance metrics for demo purposes"""
    print("📊 Creating initial performance metrics...")
    
    # Check if metrics already exist
    existing_metrics = db.query(PerformanceMetrics).first()
    if existing_metrics:
        print("✅ Performance metrics already exist, skipping...")
        return
    
    # Create metrics for the last 24 hours (every hour)
    base_time = datetime.utcnow() - timedelta(days=1)
    
    for i in range(24):
        timestamp = base_time + timedelta(hours=i)
        
        # Simulate realistic performance metrics
        metrics = PerformanceMetrics(
            timestamp=timestamp,
            api_response_time_avg=50.0 + (i % 3) * 10,  # 50-70ms
            api_response_time_95th=120.0 + (i % 5) * 20,  # 120-200ms
            database_query_time_avg=15.0 + (i % 4) * 5,  # 15-30ms
            memory_usage_percent=65.0 + (i % 10) * 2,  # 65-83%
            cpu_usage_percent=45.0 + (i % 8) * 5,  # 45-80%
            disk_usage_percent=72.0 + (i % 3) * 1,  # 72-74%
            active_connections=150 + (i % 6) * 25,  # 150-275
            requests_per_minute=450 + (i % 12) * 50,  # 450-1000
            error_rate=0.001 + (i % 5) * 0.0005  # 0.1-0.35%
        )
        db.add(metrics)
    
    db.commit()
    print("✅ Created 24 hours of initial performance metrics")

def verify_database_connection():
    """Verify database connection"""
    print("🔌 Verifying database connection...")
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    """Main function to seed admin data"""
    print("🚀 Starting admin system data seeding...")
    print("=" * 50)
    
    # Verify database connection
    if not verify_database_connection():
        print("❌ Aborting due to database connection issues")
        return False
    
    # Create database session
    db = next(get_db())
    
    try:
        # Seed data
        create_initial_admin_users(db)
        create_system_configs(db)
        create_notification_settings(db)
        create_initial_performance_metrics(db)
        
        print("=" * 50)
        print("✅ Admin system data seeding completed successfully!")
        print()
        print("🔑 Admin Login Credentials:")
        print("   • Super Admin: superadmin / Admin123!")
        print("   • Admin: admin / Demo123!")
        print("   • Operator: operator / Operator123!")
        print("   • Viewer: viewer / Viewer123!")
        print()
        print("🌐 You can now access the admin API endpoints at:")
        print("   • Admin Auth: POST /api/v1/admin/auth/login")
        print("   • Admin Dashboard: GET /api/v1/admin/dashboard") 
        print("   • API Documentation: http://localhost:8000/docs")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)