import re
from fastapi import APIRouter, HTTPException, Depends, status, Header
from fastapi import Request  # Add this import for the rate limiter
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models.user import UserCreate, User, UserRole
from app.database.database import get_users_collection
from app.utils.auth import get_password_hash, verify_password, create_access_token
from jose import JWTError, jwt
from bson import ObjectId
from datetime import timedelta, datetime
import os

# Initialize rate limiter for this router
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> bool:
    # Min 8 chars, 1 uppercase, 1 number, 1 special char
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
    # 10 digits
    pattern = r'^\d{10}$'
    return re.match(pattern, mobile) is not None

@router.post("/register")
@limiter.limit("5/minute")  # Limit registration attempts
async def register(request: Request, user: UserCreate):
    # Validate email format
    if not validate_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Check password length to ensure it doesn't exceed bcrypt 72-byte limit
    password_bytes = user.password.encode('utf-8')
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be longer than 72 characters due to security limitations"
        )
    
    # Validate password strength
    if not validate_password(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with 1 uppercase letter, 1 number, and 1 special character"
        )
    
    # Validate mobile number
    if not validate_mobile(user.mobile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile number must be 10 digits"
        )
    
    # Validate role
    if user.role not in [UserRole.JOB_SEEKER, UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'job_seeker', 'employer', or 'admin'"
        )
    
    # Get users collection in the current request context
    users_collection = get_users_collection()
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    # Create user document
    user_dict = user.model_dump()  # Updated for Pydantic v2
    user_dict["hashed_password"] = hashed_password
    user_dict["is_verified"] = False
    user_dict["is_active"] = True
    user_dict["created_at"] = datetime.now()
    
    # Insert user into database with unique email constraint (atomic operation)
    try:
        result = await users_collection.insert_one(user_dict)
        user_dict["id"] = str(result.inserted_id)
    except Exception as db_error:
        # If database is unavailable during registration, raise an error
        # Log the actual error for debugging
        print(f"Database error during registration insert: {db_error}")
        # Check if this is a duplicate key error (email already exists)
        error_str = str(db_error).lower()
        if "duplicate" in error_str or "e11000" in error_str or "E11000" in str(db_error):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Registration failed."
            )
    
    # Create access token with role information
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires,
        user_role=user.role.value  # Pass the role to be included in the token
    )
    
    # Return success response
    return {
        "success": True,
        "token": access_token,
        "user": {
            "id": user_dict["id"],
            "email": user_dict["email"],
            "name": user_dict["full_name"],
            "role": user_dict["role"]
        }
    }

@router.post("/login")
@limiter.limit("10/minute")  # Limit login attempts
async def login(request: Request, email: str = "", password: str = ""):
    # For backward compatibility, try to get email and password from form data if not provided as parameters
    if not email or not password:
        # If not provided as parameters, try to get from request body
        try:
            body = await request.json()
            email = body.get("email", email)
            password = body.get("password", password)
        except:
            pass
    
    # Ensure password is not longer than 72 characters to comply with bcrypt limitations
    if len(password) > 72:
        password = password[:72]
    
    # Check password length to ensure it doesn't exceed bcrypt 72-byte limit
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be longer than 72 characters due to security limitations"
        )
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    # Get users collection in the current request context
    users_collection = get_users_collection()
    
    # Find user by email (with error handling)
    try:
        user = await users_collection.find_one({"email": email})
        if not user:
            # Don't reveal if email exists or not - use generic message
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not verify_password(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if account is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Extract the role from the database user
        user_role = user.get("role", "job_seeker")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as db_error:
        # If database is unavailable during login, raise an error
        print(f"Database error during login: {db_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again later."
        )
    
    # Create access token with role information
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, 
        expires_delta=access_token_expires,
        user_role=user_role
    )
    
    # Return success response
    return {
        "success": True,
        "token": access_token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user["full_name"],
            "role": user_role  # Use the role we determined
        }
    }

@router.get("/me")
async def get_current_user(request: Request, authorization: str = Header(None)):
    # Validate authorization header format
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid format"
        )
    
    # Extract token from Bearer header
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Get secret key
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error"
        )
    
    # Get algorithm
    algorithm = os.getenv("ALGORITHM", "HS256")
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    
    # Get users collection in the current request context
    users_collection = get_users_collection()
    
    # Try to get user from database
    try:
        user = await users_collection.find_one({"email": email})
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    except Exception as db_error:
        # If database is unavailable during get_current_user, raise an error
        print(f"Database error during get_current_user: {db_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again later."
        )
    
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["full_name"],
        "role": user.get("role", "job_seeker")
    }