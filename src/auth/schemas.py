from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class User(UserInDB):
    pass

# Unified Login Request
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Unified User Response (for both regular users and admins)
class UnifiedUser(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    roles: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    # Fields for regular users
    name: Optional[str] = None
    
    # Fields for admin users
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_2fa_enabled: Optional[bool] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Unified Auth Response
class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UnifiedUser

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

# Legacy schema for backward compatibility
class UserLogin(BaseModel):
    email: EmailStr
    password: str