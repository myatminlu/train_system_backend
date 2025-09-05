from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models import User, Role, UserHasRole, AdminUser
from src.auth.schemas import UserCreate, UserUpdate, LoginRequest, UnifiedUser
from src.auth.utils import get_password_hash, verify_password
from typing import Optional, Union
from datetime import datetime

class UserService:
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(user.password)
        db_user = User(
            name=user.name,
            email=user.email,
            password=hashed_password
        )
        
        try:
            db.add(db_user)
            db.flush()
            
            # Assign default 'user' role
            user_role = db.query(Role).filter(Role.name == "user").first()
            if user_role:
                user_has_role = UserHasRole(user_id=db_user.id, role_id=user_role.id)
                db.add(user_has_role)
            
            db.commit()
            db.refresh(db_user)
            return db_user
            
        except IntegrityError:
            db.rollback()
            raise ValueError("Email already registered")
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = UserService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        return user
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user information"""
        db_user = UserService.get_user_by_id(db, user_id)
        if not db_user:
            return None
        
        update_data = user_update.dict(exclude_unset=True)
        
        # Hash password if it's being updated
        if "password" in update_data:
            update_data["password"] = get_password_hash(update_data["password"])
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        try:
            db.commit()
            db.refresh(db_user)
            return db_user
        except IntegrityError:
            db.rollback()
            raise ValueError("Email already exists")
    
    @staticmethod
    def get_user_roles(db: Session, user_id: int) -> list:
        """Get user's roles"""
        user_roles = db.query(UserHasRole).filter(UserHasRole.user_id == user_id).all()
        roles = []
        for user_role in user_roles:
            role = db.query(Role).filter(Role.id == user_role.role_id).first()
            if role:
                roles.append(role.name)
        return roles
    
    @staticmethod
    def get_admin_by_email(db: Session, email: str) -> Optional[AdminUser]:
        """Get admin user by email"""
        return db.query(AdminUser).filter(AdminUser.email == email).first()
    
    @staticmethod
    def authenticate_unified(db: Session, login_data: LoginRequest) -> Optional[UnifiedUser]:
        """Unified authentication for both regular users and admin users"""
        # First check if it's a regular user
        user = UserService.get_user_by_email(db, login_data.email)
        if user and verify_password(login_data.password, user.password):
            # Get user roles
            roles = UserService.get_user_roles(db, user.id)
            
            # Check if user has admin role
            is_admin = 'admin' in roles or 'super_admin' in roles
            
            return UnifiedUser(
                id=user.id,
                email=user.email,
                name=user.name,
                is_admin=is_admin,
                roles=roles,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        
        # Check if it's an admin user
        admin = UserService.get_admin_by_email(db, login_data.email)
        if admin and verify_password(login_data.password, admin.password_hash):
            # For admin users, include their role as a permission
            permissions = [admin.role]  # Just use the role for now, permissions can be expanded later
            
            # Update last login
            admin.last_login = datetime.utcnow()
            db.commit()
            
            return UnifiedUser(
                id=admin.id,
                email=admin.email,
                username=admin.username,
                full_name=admin.full_name,
                is_admin=True,
                roles=permissions,
                is_active=admin.is_active,
                is_2fa_enabled=admin.is_2fa_enabled,
                last_login=admin.last_login,
                created_at=admin.created_at,
                updated_at=admin.updated_at
            )
        
        return None
    
    @staticmethod
    def get_unified_user_by_id(db: Session, user_id: int) -> Optional[UnifiedUser]:
        """Get unified user information by ID (works for both regular users and admin users)"""
        # First check if it's a regular user
        user = UserService.get_user_by_id(db, user_id)
        if user:
            # Get user roles
            roles = UserService.get_user_roles(db, user.id)
            
            # Check if user has admin role
            is_admin = 'admin' in roles or 'super_admin' in roles
            
            return UnifiedUser(
                id=user.id,
                email=user.email,
                name=user.name,
                is_admin=is_admin,
                roles=roles,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        
        # Check if it's an admin user
        admin = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if admin:
            # For admin users, include their role as a permission
            permissions = [admin.role]  # Just use the role for now, permissions can be expanded later
            
            return UnifiedUser(
                id=admin.id,
                email=admin.email,
                username=admin.username,
                full_name=admin.full_name,
                is_admin=True,
                roles=permissions,
                is_active=admin.is_active,
                is_2fa_enabled=admin.is_2fa_enabled,
                last_login=admin.last_login,
                created_at=admin.created_at,
                updated_at=admin.updated_at
            )
        
        return None