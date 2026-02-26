from fastapi import APIRouter, HTTPException, Depends, status, Header, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import UserCreate, User as UserSchema, UserRole
from app.database.database import get_db
from app.database.models import User as UserModel
from app.utils.auth import get_password_hash, verify_password, create_access_token
from jose import JWTError, jwt
from datetime import timedelta, datetime
import os
import uuid
import re

# Initialize rate limiter for this router
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

def validate_mobile(mobile: str) -> bool:
    pattern = r'^\d{10}$'
    return re.match(pattern, mobile) is not None

@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)):
    if not validate_email(user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
    
    password_bytes = user.password.encode('utf-8')
    if len(password_bytes) > 72:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password too long")
    
    if not validate_password(user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password too weak")
    
    if not validate_mobile(user.mobile):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mobile must be 10 digits")
    
    # Check if user already exists
    stmt = select(UserModel).where(UserModel.email == user.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    
    hashed_password = get_password_hash(user.password)
    
    db_user = UserModel(
        id=str(uuid.uuid4()),
        email=user.email,
        full_name=user.full_name,
        password=hashed_password,
        role=user.role.value,
        mobile=user.mobile,
        is_verified=False,
        is_active=True
    )
    
    try:
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    except Exception as e:
        await db.rollback()
        print(f"Registration error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires,
        user_role=user.role.value
    )
    
    return {
        "success": True,
        "token": access_token,
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.full_name,
            "role": db_user.role
        }
    }

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
    except:
        raise HTTPException(status_code=400, detail="Invalid request body")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    stmt = select(UserModel).where(UserModel.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account deactivated")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires,
        user_role=user.role
    )
    
    return {
        "success": True,
        "token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "role": user.role
        }
    }

@router.get("/me")
async def get_me(request: Request, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    token = authorization[7:]
    secret_key = os.getenv("SECRET_KEY")
    algorithm = os.getenv("ALGORITHM", "HS256")
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    stmt = select(UserModel).where(UserModel.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "role": user.role
    }
