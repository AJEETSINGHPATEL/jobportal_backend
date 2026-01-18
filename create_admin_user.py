import asyncio
import os
import sys
from datetime import datetime
from bson import ObjectId

# Add the backend directory to the Python path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.database.database import get_users_collection
from app.utils.auth import get_password_hash
from app.models.user import UserRole

async def create_admin_user():
    """Create a default admin user if one doesn't exist"""
    users_collection = get_users_collection()
    
    # Check if admin user already exists
    existing_admin = await users_collection.find_one({"email": "admin@admin.com"})
    
    if existing_admin:
        print("Admin user already exists!")
        print(f"Email: admin@admin.com")
        print(f"Password: Admin@123")
        print(f"Role: {existing_admin.get('role', 'admin')}")
        return
    
    # Hash the password
    password_hash = get_password_hash("Admin@123")
    
    # Create admin user document
    admin_user = {
        "full_name": "Admin User",
        "email": "admin@admin.com",
        "password": "Admin@123",  # This will be hashed
        "hashed_password": password_hash,
        "mobile": "0000000000",  # Default mobile for admin
        "role": "admin",
        "is_verified": True,
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    try:
        # Insert the admin user
        result = await users_collection.insert_one(admin_user)
        print("Admin user created successfully!")
        print(f"Email: admin@admin.com")
        print(f"Password: Admin@123")
        print(f"User ID: {result.inserted_id}")
    except Exception as e:
        print(f"Error creating admin user: {e}")

if __name__ == "__main__":
    asyncio.run(create_admin_user())