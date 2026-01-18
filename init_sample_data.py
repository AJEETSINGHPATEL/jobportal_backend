import asyncio
from app.database.database import users_collection, jobs_collection, applications_collection, saved_jobs_collection
from app.utils.auth import get_password_hash
from datetime import datetime
import uuid

async def init_sample_data():
    """Initialize database with sample data"""
    
    # Clear existing data
    await users_collection.delete_many({})
    await jobs_collection.delete_many({})
    await applications_collection.delete_many({})
    await saved_jobs_collection.delete_many({})
    
    # Create sample users
    users = [
        {
            "email": "jobseeker@example.com",
            "hashed_password": get_password_hash("Password123!"),
            "full_name": "John Doe",
            "role": "job_seeker",
            "mobile": "9876543210",
            "is_verified": True,
            "created_at": datetime.now()
        },
        {
            "email": "employer@example.com",
            "hashed_password": get_password_hash("Password123!"),
            "full_name": "Jane Smith",
            "role": "employer",
            "mobile": "9876543211",
            "is_verified": True,
            "created_at": datetime.now()
        }
    ]
    
    user_results = await users_collection.insert_many(users)
    job_seeker_id = user_results.inserted_ids[0]
    employer_id = user_results.inserted_ids[1]
    
    # Create sample jobs
    jobs = [
        {
            "title": "Senior Software Engineer",
            "description": "We are looking for an experienced software engineer to join our team. You will be responsible for developing and maintaining our web applications.",
            "company": "Tech Corp",
            "salary_min": 800000,
            "salary_max": 1200000,
            "location": "Bangalore",
            "skills": ["Python", "Django", "React", "AWS"],
            "experience_required": "3-5 years",
            "work_mode": "Hybrid",
            "company_logo_url": "",
            "company_rating": 4.2,
            "reviews_count": 1200,
            "posted_by": str(employer_id),
            "posted_at": datetime.now(),
            "is_active": True,
            "application_count": 0,
            "view_count": 0
        },
        {
            "title": "Product Manager",
            "description": "Join our product team to drive innovation and growth. You will work closely with engineering and design teams to deliver exceptional products.",
            "company": "Innovate Inc",
            "salary_min": 1000000,
            "salary_max": 1500000,
            "location": "Mumbai",
            "skills": ["Product Management", "Agile", "Analytics", "Leadership"],
            "experience_required": "5-8 years",
            "work_mode": "Remote",
            "company_logo_url": "",
            "company_rating": 4.5,
            "reviews_count": 800,
            "posted_by": str(employer_id),
            "posted_at": datetime.now(),
            "is_active": True,
            "application_count": 0,
            "view_count": 0
        },
        {
            "title": "Data Scientist",
            "description": "We are seeking a data scientist to help us extract insights from our data and build predictive models.",
            "company": "Data Insights Ltd",
            "salary_min": 900000,
            "salary_max": 1300000,
            "location": "Hyderabad",
            "skills": ["Python", "Machine Learning", "SQL", "Statistics"],
            "experience_required": "2-4 years",
            "work_mode": "On-site",
            "company_logo_url": "",
            "company_rating": 4.0,
            "reviews_count": 650,
            "posted_by": str(employer_id),
            "posted_at": datetime.now(),
            "is_active": True,
            "application_count": 0,
            "view_count": 0
        }
    ]
    
    job_results = await jobs_collection.insert_many(jobs)
    
    print("Sample data initialized successfully!")
    print(f"Created {len(users)} users")
    print(f"Created {len(jobs)} jobs")

if __name__ == "__main__":
    asyncio.run(init_sample_data())