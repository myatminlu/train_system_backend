from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.database import get_db
from src.auth.utils import verify_token
from src.auth.service import UserService
from src.auth.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token and get payload
    token_data = verify_token(token, credentials_exception)
    
    # Get user from database
    user = UserService.get_user_by_id(db, user_id=token_data["user_id"])
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user (can be extended with user status check)"""
    return current_user

def require_admin(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Require admin role for access"""
    user_roles = UserService.get_user_roles(db, current_user.id)
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user