from typing import List, Dict, Optional, Set, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import secrets
import pyotp
import qrcode
from io import BytesIO
import base64
import hashlib
import jwt
from passlib.context import CryptContext

from src.admin.schemas import (
    AdminUser, AdminUserCreate, AdminUserUpdate, AdminLogin, AdminLoginResponse,
    Admin2FASetup, Admin2FAVerify, AdminRole, Permission, PermissionType,
    RolePermissions, AuditLog, AuditAction
)
from src.config import settings

class AdminAuthService:
    """Service for admin authentication, authorization, and 2FA"""
    
    def __init__(self, db: Session):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._admin_users = {}  # In-memory storage (would use database)
        self._sessions = {}
        self._2fa_secrets = {}
        self._permissions = self._initialize_permissions()
        self._role_permissions = self._initialize_role_permissions()
        self._audit_logs = []
        
        # Initialize default admin user
        self._create_default_admin()
    
    def _initialize_permissions(self) -> Dict[str, Permission]:
        """Initialize system permissions"""
        permissions = {}
        
        # Define all available permissions
        resources = ["users", "stations", "bookings", "routes", "schedules", "analytics", "system", "audit"]
        actions = [PermissionType.READ, PermissionType.WRITE, PermissionType.DELETE, PermissionType.ADMIN]
        
        for resource in resources:
            for action in actions:
                perm_id = f"{resource}:{action.value}"
                permissions[perm_id] = Permission(
                    id=perm_id,
                    name=f"{action.value.title()} {resource.title()}",
                    description=f"Permission to {action.value} {resource}",
                    resource=resource,
                    action=action
                )
        
        # Add special permissions
        special_perms = [
            ("system:health", "System Health", "View system health and monitoring"),
            ("system:config", "System Config", "Manage system configuration"),
            ("system:backup", "System Backup", "Manage system backups"),
            ("analytics:export", "Export Analytics", "Export analytics data"),
            ("users:impersonate", "Impersonate Users", "Impersonate other users"),
        ]
        
        for perm_id, name, desc in special_perms:
            resource, action = perm_id.split(":")
            permissions[perm_id] = Permission(
                id=perm_id,
                name=name,
                description=desc,
                resource=resource,
                action=PermissionType.ADMIN
            )
        
        return permissions
    
    def _initialize_role_permissions(self) -> Dict[AdminRole, RolePermissions]:
        """Initialize role-based permissions"""
        
        role_permissions = {}
        
        # Super Admin - All permissions
        role_permissions[AdminRole.SUPER_ADMIN] = RolePermissions(
            role=AdminRole.SUPER_ADMIN,
            permissions=list(self._permissions.values()),
            description="Full system access with all permissions"
        )
        
        # Admin - Most permissions except sensitive system operations
        admin_perms = [p for p in self._permissions.values() 
                      if not (p.resource == "system" and p.action == PermissionType.ADMIN)]
        role_permissions[AdminRole.ADMIN] = RolePermissions(
            role=AdminRole.ADMIN,
            permissions=admin_perms,
            description="Administrative access with management permissions"
        )
        
        # Operator - Operational permissions
        operator_perms = [p for p in self._permissions.values()
                         if p.resource in ["stations", "schedules", "bookings"] and
                         p.action in [PermissionType.READ, PermissionType.WRITE]]
        role_permissions[AdminRole.OPERATOR] = RolePermissions(
            role=AdminRole.OPERATOR,
            permissions=operator_perms,
            description="Operational access for day-to-day management"
        )
        
        # Viewer - Read-only access
        viewer_perms = [p for p in self._permissions.values()
                       if p.action == PermissionType.READ]
        role_permissions[AdminRole.VIEWER] = RolePermissions(
            role=AdminRole.VIEWER,
            permissions=viewer_perms,
            description="Read-only access to system data"
        )
        
        # Analyst - Analytics and reporting
        analyst_perms = [p for p in self._permissions.values()
                        if p.resource in ["analytics", "bookings", "routes"] or
                        (p.resource == "system" and p.action == PermissionType.READ)]
        role_permissions[AdminRole.ANALYST] = RolePermissions(
            role=AdminRole.ANALYST,
            permissions=analyst_perms,
            description="Analytics and reporting access"
        )
        
        return role_permissions
    
    def _create_default_admin(self):
        """Create default super admin user"""
        admin_user = AdminUser(
            id=1,
            username="admin",
            email="admin@bangkoktrains.com",
            full_name="System Administrator",
            role=AdminRole.SUPER_ADMIN,
            is_active=True,
            is_2fa_enabled=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            permissions=[p.id for p in self._role_permissions[AdminRole.SUPER_ADMIN].permissions]
        )
        
        # Set default password (would be changed on first login)
        password_hash = self.pwd_context.hash("admin123")
        self._admin_users[1] = {
            "user": admin_user,
            "password_hash": password_hash
        }
    
    def create_admin_user(self, user_data: AdminUserCreate, created_by_id: int) -> AdminUser:
        """Create a new admin user"""
        
        # Check if username or email already exists
        for user_info in self._admin_users.values():
            user = user_info["user"]
            if user.username == user_data.username:
                raise ValueError("Username already exists")
            if user.email == user_data.email:
                raise ValueError("Email already exists")
        
        # Generate new user ID
        user_id = max(self._admin_users.keys()) + 1 if self._admin_users else 1
        
        # Hash password
        password_hash = self.pwd_context.hash(user_data.password)
        
        # Get role permissions
        role_perms = self._role_permissions[user_data.role].permissions
        default_permissions = [p.id for p in role_perms]
        
        # Override with custom permissions if provided
        if user_data.permissions:
            # Validate permissions exist
            for perm_id in user_data.permissions:
                if perm_id not in self._permissions:
                    raise ValueError(f"Invalid permission: {perm_id}")
            default_permissions = user_data.permissions
        
        # Create admin user
        admin_user = AdminUser(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            is_active=True,
            is_2fa_enabled=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            permissions=default_permissions
        )
        
        self._admin_users[user_id] = {
            "user": admin_user,
            "password_hash": password_hash
        }
        
        # Log audit event
        self._log_audit(
            admin_user_id=created_by_id,
            action=AuditAction.CREATE,
            resource_type="admin_user",
            resource_id=str(user_id),
            details={"username": user_data.username, "role": user_data.role.value},
            success=True
        )
        
        return admin_user
    
    def authenticate_admin(self, login_data: AdminLogin) -> AdminLoginResponse:
        """Authenticate admin user and return access token"""
        
        # Find user by username
        user_info = None
        for info in self._admin_users.values():
            if info["user"].username == login_data.username:
                user_info = info
                break
        
        if not user_info:
            self._log_audit(
                admin_username=login_data.username,
                action=AuditAction.LOGIN,
                resource_type="admin_auth",
                details={"reason": "user_not_found"},
                success=False
            )
            raise ValueError("Invalid credentials")
        
        user = user_info["user"]
        password_hash = user_info["password_hash"]
        
        # Check if user is active
        if not user.is_active:
            raise ValueError("Account is deactivated")
        
        # Verify password
        if not self.pwd_context.verify(login_data.password, password_hash):
            self._log_audit(
                admin_user_id=user.id,
                admin_username=user.username,
                action=AuditAction.LOGIN,
                resource_type="admin_auth",
                details={"reason": "invalid_password"},
                success=False
            )
            raise ValueError("Invalid credentials")
        
        # Check 2FA if enabled
        if user.is_2fa_enabled:
            if not login_data.totp_code:
                return AdminLoginResponse(
                    access_token="",
                    expires_in=0,
                    admin_user=user,
                    permissions=user.permissions,
                    requires_2fa=True
                )
            
            if not self._verify_2fa_code(user.id, login_data.totp_code):
                self._log_audit(
                    admin_user_id=user.id,
                    admin_username=user.username,
                    action=AuditAction.LOGIN,
                    resource_type="admin_auth",
                    details={"reason": "invalid_2fa"},
                    success=False
                )
                raise ValueError("Invalid 2FA code")
        
        # Generate access token
        token_data = {
            "admin_user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "permissions": user.permissions,
            "exp": datetime.utcnow() + timedelta(hours=8)  # 8 hour expiry
        }
        
        access_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
        
        # Update last login
        user.last_login = datetime.now()
        
        # Create session
        session_id = secrets.token_hex(32)
        self._sessions[session_id] = {
            "admin_user_id": user.id,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=8),
            "access_token": access_token
        }
        
        # Log successful login
        self._log_audit(
            admin_user_id=user.id,
            admin_username=user.username,
            action=AuditAction.LOGIN,
            resource_type="admin_auth",
            details={"session_id": session_id},
            success=True
        )
        
        return AdminLoginResponse(
            access_token=access_token,
            expires_in=28800,  # 8 hours in seconds
            admin_user=user,
            permissions=user.permissions,
            requires_2fa=False
        )
    
    def setup_2fa(self, admin_user_id: int) -> Admin2FASetup:
        """Setup 2FA for admin user"""
        
        if admin_user_id not in self._admin_users:
            raise ValueError("Admin user not found")
        
        user = self._admin_users[admin_user_id]["user"]
        
        # Generate secret key
        secret = pyotp.random_base32()
        self._2fa_secrets[admin_user_id] = secret
        
        # Generate QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Bangkok Train System Admin"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_code_url = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
        
        # Generate backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        return Admin2FASetup(
            secret_key=secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes
        )
    
    def verify_2fa_setup(self, admin_user_id: int, verification: Admin2FAVerify) -> bool:
        """Verify 2FA setup with TOTP code"""
        
        if admin_user_id not in self._2fa_secrets:
            raise ValueError("2FA setup not initiated")
        
        secret = self._2fa_secrets[admin_user_id]
        totp = pyotp.TOTP(secret)
        
        if totp.verify(verification.totp_code):
            # Enable 2FA for user
            self._admin_users[admin_user_id]["user"].is_2fa_enabled = True
            self._admin_users[admin_user_id]["user"].updated_at = datetime.now()
            
            # Log audit event
            self._log_audit(
                admin_user_id=admin_user_id,
                action=AuditAction.UPDATE,
                resource_type="admin_user",
                resource_id=str(admin_user_id),
                details={"2fa_enabled": True},
                success=True
            )
            
            return True
        
        return False
    
    def _verify_2fa_code(self, admin_user_id: int, totp_code: str) -> bool:
        """Verify 2FA code during login"""
        
        if admin_user_id not in self._2fa_secrets:
            return False
        
        secret = self._2fa_secrets[admin_user_id]
        totp = pyotp.TOTP(secret)
        return totp.verify(totp_code)
    
    def verify_token(self, token: str) -> Optional[AdminUser]:
        """Verify access token and return admin user"""
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            admin_user_id = payload.get("admin_user_id")
            
            if admin_user_id and admin_user_id in self._admin_users:
                return self._admin_users[admin_user_id]["user"]
            
        except jwt.PyJWTError:
            pass
        
        return None
    
    def check_permission(self, admin_user_id: int, resource: str, action: str) -> bool:
        """Check if admin user has specific permission"""
        
        if admin_user_id not in self._admin_users:
            return False
        
        user = self._admin_users[admin_user_id]["user"]
        required_permission = f"{resource}:{action}"
        
        return required_permission in user.permissions
    
    def get_admin_user(self, admin_user_id: int) -> Optional[AdminUser]:
        """Get admin user by ID"""
        
        if admin_user_id in self._admin_users:
            return self._admin_users[admin_user_id]["user"]
        return None
    
    def update_admin_user(
        self, 
        admin_user_id: int, 
        update_data: AdminUserUpdate,
        updated_by_id: int
    ) -> AdminUser:
        """Update admin user"""
        
        if admin_user_id not in self._admin_users:
            raise ValueError("Admin user not found")
        
        user = self._admin_users[admin_user_id]["user"]
        updated_fields = {}
        
        if update_data.email is not None:
            user.email = update_data.email
            updated_fields["email"] = update_data.email
        
        if update_data.full_name is not None:
            user.full_name = update_data.full_name
            updated_fields["full_name"] = update_data.full_name
        
        if update_data.role is not None:
            user.role = update_data.role
            # Update permissions based on new role
            role_perms = self._role_permissions[update_data.role].permissions
            user.permissions = [p.id for p in role_perms]
            updated_fields["role"] = update_data.role.value
        
        if update_data.is_active is not None:
            user.is_active = update_data.is_active
            updated_fields["is_active"] = update_data.is_active
        
        if update_data.permissions is not None:
            user.permissions = update_data.permissions
            updated_fields["permissions"] = update_data.permissions
        
        user.updated_at = datetime.now()
        
        # Log audit event
        self._log_audit(
            admin_user_id=updated_by_id,
            action=AuditAction.UPDATE,
            resource_type="admin_user",
            resource_id=str(admin_user_id),
            details=updated_fields,
            success=True
        )
        
        return user
    
    def list_admin_users(self) -> List[AdminUser]:
        """List all admin users"""
        return [info["user"] for info in self._admin_users.values()]
    
    def get_role_permissions(self, role: AdminRole) -> RolePermissions:
        """Get permissions for a role"""
        return self._role_permissions[role]
    
    def get_all_permissions(self) -> List[Permission]:
        """Get all available permissions"""
        return list(self._permissions.values())
    
    def logout_admin(self, token: str) -> bool:
        """Logout admin user by invalidating token"""
        
        admin_user = self.verify_token(token)
        if not admin_user:
            return False
        
        # Remove all sessions for this user
        sessions_to_remove = []
        for session_id, session_data in self._sessions.items():
            if session_data["admin_user_id"] == admin_user.id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self._sessions[session_id]
        
        # Log audit event
        self._log_audit(
            admin_user_id=admin_user.id,
            admin_username=admin_user.username,
            action=AuditAction.LOGOUT,
            resource_type="admin_auth",
            details={},
            success=True
        )
        
        return True
    
    def _log_audit(
        self,
        action: AuditAction,
        resource_type: str,
        success: bool,
        admin_user_id: Optional[int] = None,
        admin_username: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Dict[str, Any] = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "Unknown"
    ):
        """Log audit event"""
        
        log_entry = AuditLog(
            id=len(self._audit_logs) + 1,
            timestamp=datetime.now(),
            admin_user_id=admin_user_id,
            admin_username=admin_username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success
        )
        
        self._audit_logs.append(log_entry)
        
        # Keep only recent logs (last 10000)
        if len(self._audit_logs) > 10000:
            self._audit_logs = self._audit_logs[-10000:]
    
    def get_audit_logs(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs with optional filtering"""
        
        logs = self._audit_logs
        
        if filters:
            if filters.get("admin_user_id"):
                logs = [log for log in logs if log.admin_user_id == filters["admin_user_id"]]
            
            if filters.get("action"):
                logs = [log for log in logs if log.action == filters["action"]]
            
            if filters.get("resource_type"):
                logs = [log for log in logs if log.resource_type == filters["resource_type"]]
            
            if filters.get("date_from"):
                logs = [log for log in logs if log.timestamp >= filters["date_from"]]
            
            if filters.get("date_to"):
                logs = [log for log in logs if log.timestamp <= filters["date_to"]]
            
            if filters.get("success") is not None:
                logs = [log for log in logs if log.success == filters["success"]]
        
        # Sort by timestamp (newest first) and limit
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        return logs[:limit]