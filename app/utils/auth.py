from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from bson import ObjectId
import os
from dotenv import load_dotenv
from typing import Optional
import secrets
import bcrypt

load_dotenv()

# Password hashing - using bcrypt directly to avoid backend compatibility issues
pwd_context = CryptContext(schemes=["plaintext"], deprecated="auto")  # Placeholder context

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def verify_password(plain_password, hashed_password):
    # Ensure password is not longer than 72 bytes to comply with bcrypt limitations
    # Convert to bytes and truncate if necessary, then decode back to string
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        # Decode back to string, handling potential multi-byte character cuts
        plain_password = password_bytes.decode('utf-8', errors='ignore')
    else:
        plain_password = password_bytes.decode('utf-8')
    
    try:
        # Use bcrypt directly to avoid backend initialization issues
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def get_password_hash(password):
    # Ensure password is not longer than 72 bytes to comply with bcrypt limitations
    # Convert to bytes and truncate if necessary, then decode back to string
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        # Decode back to string, handling potential multi-byte character cuts
        password = password_bytes.decode('utf-8', errors='ignore')
    else:
        password = password_bytes.decode('utf-8')
    
    try:
        # Use bcrypt directly to avoid backend initialization issues
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        # Return as string for storage
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
        
        # Include role in token if provided
        if user_role:
            to_encode.update({"role": user_role})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print(f"Error creating access token: {e}")
        raise

async def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise Exception("Could not validate credentials - no email in token")
        
        # Extract role from token
        role = payload.get("role", "job_seeker")  # Default to job_seeker if no role is present
        
        # Check if token is expired (double-check using exp claim)
        import time
        expiry_timestamp = payload.get("exp", 0)
        if expiry_timestamp < time.time():
            raise Exception("Token has expired")
        
        # We need to fetch the user's ID from the database
        # Import here to avoid circular imports
        from app.database.database import get_users_collection
        
        # Get users collection in the current request context
        users_collection = get_users_collection()
        
        # Find user by email to get the ID
        user = await users_collection.find_one({"email": email})
        if not user:
            raise Exception("User not found")
        
        # Return user info including ID
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": role
        }
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise Exception("Could not validate credentials - JWT error")
    except Exception as e:
        print(f"General error in get_current_user: {e}")
        raise Exception("Could not validate credentials")

async def get_current_user_role(user_id: str):
    try:
        from app.database.database import get_users_collection
        
        # Get users collection in the current request context
        users_collection = get_users_collection()
        
        # Find user by ID
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise Exception("User not found")
        
        # Return user role
        return user.get("role", "job_seeker")
    except Exception as e:
        print(f"Error getting user role: {e}")
        raise Exception("Could not get user role")
