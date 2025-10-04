from fastapi import APIRouter, HTTPException, status
from uuid import uuid4
from datetime import timedelta

from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse
from app.models.user import User, users_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings

router = APIRouter()


@router.post("/register", response_model=dict)
async def register(user_data: UserCreate):
    # Check if user exists
    if any(u.username == user_data.username for u in users_db.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Create new user
    user_id = str(uuid4())
    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        id=user_id,
        username=user_data.username,
        hashed_password=hashed_password
    )

    users_db[user_id] = new_user

    # Create access token
    access_token = create_access_token(
        data={"sub": user_data.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "message": "User registered successfully",
        "token": access_token,
        "user": UserResponse(id=new_user.id, username=new_user.username)
    }


@router.post("/login", response_model=dict)
async def login(user_data: UserLogin):
    # Find user
    user = next(
        (u for u in users_db.values() if u.username == user_data.username),
        None
    )

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "message": "Login successful",
        "token": access_token,
        "user": UserResponse(id=user.id, username=user.username)
    }
