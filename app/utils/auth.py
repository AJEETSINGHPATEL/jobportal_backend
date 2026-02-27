from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from dotenv import load_dotenv
from typing import Optional
import secrets
import bcrypt
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def verify_password(plain_password, hashed_password):
    try:
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
            plain_password = password_bytes.decode('utf-8', errors='ignore')
        else:
            plain_password = password_bytes.decode('utf-8')
        
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def get_password_hash(password):
    try:
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
            password = password_bytes.decode('utf-8', errors='ignore')
        else:
            password = password_bytes.decode('utf-8')
        
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"Error hashing password: {e}")
        raise

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, user_role: Optional[str] = None):
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        
        if user_role:
            to_encode.update({"role": user_role})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print(f"Error creating access token: {e}")
        raise

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(token: str) -> dict:
    """Internal helper to verify token and return user dict"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    if email is None:
        raise Exception("Invalid token")
    
    expiry = payload.get("exp", 0)
    if expiry < time.time():
        raise Exception("Token expired")
    
    from app.database.database import AsyncSessionLocal
    from app.database.models import User
    
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise Exception("User not found")
        
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name
        }

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    FastAPI dependency to get current user info from token. 
    Required - raises 401 if missing or invalid.
    """
    try:
        return await verify_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

optional_security = HTTPBearer(auto_error=False)

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)) -> Optional[dict]:
    """
    FastAPI dependency to optionally get current user info.
    Returns None if token is missing or invalid instead of raising 401.
    """
    if not credentials:
        return None
    try:
        return await verify_token(credentials.credentials)
    except:
        return None

async def get_current_user_role(user_id: str):
    try:
        from app.database.database import AsyncSessionLocal
        from app.database.models import User
        
        async with AsyncSessionLocal() as db:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                raise Exception("User not found")
            return user.role
    except Exception as e:
        print(f"Error getting user role: {e}")
        raise Exception("Could not get user role")
