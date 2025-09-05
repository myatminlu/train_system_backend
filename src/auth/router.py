from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from src.database import get_db
from src.auth.schemas import UserCreate, User, Token, UserUpdate, LoginRequest, AuthResponse, UnifiedUser
from src.auth.service import UserService
from src.auth.utils import create_access_token
from src.auth.dependencies import get_current_user
from src.config import settings

router = APIRouter()

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        db_user = UserService.create_user(db=db, user=user)
        return db_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=AuthResponse)
def login_unified(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Unified login for both regular users and admin users"""
    user = UserService.authenticate_unified(db, login_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "is_admin": user.is_admin}, expires_delta=access_token_expires
    )
    return AuthResponse(
        access_token=access_token, 
        token_type="bearer",
        user=user
    )

@router.get("/me", response_model=UnifiedUser)
def read_users_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user profile"""
    unified_user = UserService.get_unified_user_by_id(db, current_user.id)
    if not unified_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return unified_user

@router.put("/me", response_model=User)
def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    try:
        updated_user = UserService.update_user(db=db, user_id=current_user.id, user_update=user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )