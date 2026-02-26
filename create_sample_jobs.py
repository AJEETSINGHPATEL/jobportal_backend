import asyncio
from app.database.database import jobs_collection
from datetime import datetime
from app.models.job import JobType, JobLocationType

async def create_sample_jobs():
    """Create sample jobs in the database for testing"""
    
    sample_jobs = [
        {
            "title": "Senior Software Engineer",
            "description": "We are looking for an experienced software engineer to join our team. You will be responsible for developing and maintaining our web applications.",
            "company": "Tech Corp",
            "salary_min": 90000,
            "salary_max": 130000,
            "location": "San Francisco, CA",
            "skills": ["Python", "JavaScript", "React", "AWS", "Docker"],
            "experience_required": "5+ years",
            "work_mode": "hybrid",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 12,
            "view_count": 156
        },
        {
            "title": "Product Manager",
            "description": "Join our product team to drive the development of innovative solutions. You will work closely with engineering, design, and marketing teams.",
            "company": "Innovate Inc",
            "salary_min": 110000,
            "salary_max": 150000,
            "location": "New York, NY",
            "skills": ["Product Strategy", "Agile", "Analytics", "User Research"],
            "experience_required": "3+ years",
            "work_mode": "onsite",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 24,
            "view_count": 203
        },
        {
            "title": "Data Scientist",
            "description": "We are seeking a data scientist to analyze large datasets and build predictive models to drive business decisions.",
            "company": "Data Insights Co",
            "salary_min": 100000,
            "salary_max": 140000,
            "location": "Remote",
            "skills": ["Python", "R", "SQL", "Machine Learning", "Statistics"],
            "experience_required": "2+ years",
            "work_mode": "remote",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 18,
            "view_count": 187
        },
        {
            "title": "Frontend Developer",
            "description": "Looking for a skilled frontend developer to build responsive and user-friendly web applications using modern JavaScript frameworks.",
            "company": "Web Solutions Ltd",
            "salary_min": 70000,
            "salary_max": 100000,
            "location": "Austin, TX",
            "skills": ["JavaScript", "React", "CSS", "HTML", "TypeScript"],
            "experience_required": "2+ years",
            "work_mode": "hybrid",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 15,
            "view_count": 142
        },
        {
            "title": "DevOps Engineer",
            "description": "Seeking a DevOps engineer to manage our cloud infrastructure and implement CI/CD pipelines for our development teams.",
            "company": "Cloud Systems Inc",
            "salary_min": 95000,
            "salary_max": 135000,
            "location": "Seattle, WA",
            "skills": ["Docker", "Kubernetes", "AWS", "Jenkins", "Terraform"],
            "experience_required": "4+ years",
            "work_mode": "remote",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 20,
            "view_count": 175
        },
        {
            "title": "UX/UI Designer",
            "description": "We need a creative UX/UI designer to create beautiful and intuitive user interfaces for our web and mobile applications.",
            "company": "Design Studio Pro",
            "salary_min": 75000,
            "salary_max": 110000,
            "location": "Los Angeles, CA",
            "skills": ["Figma", "Adobe XD", "UI Design", "User Research", "Prototyping"],
            "experience_required": "3+ years",
            "work_mode": "hybrid",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 22,
            "view_count": 168
        },
        {
            "title": "Backend Developer",
            "description": "Looking for an experienced backend developer to build and maintain server-side applications and APIs.",
            "company": "Server Logic Co",
            "salary_min": 80000,
            "salary_max": 120000,
            "location": "Chicago, IL",
            "skills": ["Python", "Django", "Node.js", "PostgreSQL", "Redis"],
            "experience_required": "3+ years",
            "work_mode": "onsite",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 16,
            "view_count": 134
        },
        {
            "title": "Cybersecurity Analyst",
            "description": "Seeking a cybersecurity analyst to protect our systems and data from security threats and vulnerabilities.",
            "company": "SecureNet Solutions",
            "salary_min": 85000,
            "salary_max": 125000,
            "location": "Washington, DC",
            "skills": ["Security", "Firewalls", "SIEM", "Incident Response", "Vulnerability Assessment"],
            "experience_required": "3+ years",
            "work_mode": "onsite",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 14,
            "view_count": 128
        },
        {
            "title": "Machine Learning Engineer",
            "description": "We are looking for a machine learning engineer to develop and deploy AI models for our data-driven products.",
            "company": "AI Innovations",
            "salary_min": 110000,
            "salary_max": 150000,
            "location": "Boston, MA",
            "skills": ["Python", "TensorFlow", "PyTorch", "Deep Learning", "NLP"],
            "experience_required": "4+ years",
            "work_mode": "hybrid",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 19,
            "view_count": 192
        },
        {
            "title": "Full Stack Developer",
            "description": "Looking for a full stack developer to work on both frontend and backend components of our web applications.",
            "company": "Digital Creations",
            "salary_min": 85000,
            "salary_max": 125000,
            "location": "Denver, CO",
            "skills": ["JavaScript", "React", "Node.js", "MongoDB", "Express"],
            "experience_required": "3+ years",
            "work_mode": "remote",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 17,
            "view_count": 156
        },
        {
            "title": "Mobile App Developer",
            "description": "Seeking an experienced mobile app developer to create iOS and Android applications using modern frameworks.",
            "company": "Mobile First Inc",
            "salary_min": 78000,
            "salary_max": 115000,
            "location": "Miami, FL",
            "skills": ["React Native", "Swift", "Kotlin", "iOS", "Android"],
            "experience_required": "2+ years",
            "work_mode": "hybrid",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 21,
            "view_count": 163
        },
        {
            "title": "Data Analyst",
            "description": "We need a data analyst to interpret data and provide insights to help drive business decisions.",
            "company": "Analytics Pro",
            "salary_min": 65000,
            "salary_max": 95000,
            "location": "Remote",
            "skills": ["SQL", "Excel", "Tableau", "Python", "Statistical Analysis"],
            "experience_required": "1+ years",
            "work_mode": "remote",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 25,
            "view_count": 189
        },
        {
            "title": "Cloud Solutions Architect",
            "description": "Looking for a cloud architect to design and implement scalable cloud solutions for our enterprise clients.",
            "company": "Cloud Systems Inc",
            "salary_min": 120000,
            "salary_max": 160000,
            "location": "San Jose, CA",
            "skills": ["AWS", "Azure", "GCP", "Architecture", "Microservices"],
            "experience_required": "6+ years",
            "work_mode": "hybrid",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 13,
            "view_count": 147
        },
        {
            "title": "QA Engineer",
            "description": "Seeking a quality assurance engineer to test our software products and ensure high quality standards.",
            "company": "Quality First Co",
            "salary_min": 70000,
            "salary_max": 100000,
            "location": "Atlanta, GA",
            "skills": ["Testing", "Selenium", "JUnit", "CI/CD", "Automation"],
            "experience_required": "2+ years",
            "work_mode": "onsite",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 11,
            "view_count": 122
        },
        {
            "title": "Technical Writer",
            "description": "We need a technical writer to create documentation for our software products and APIs.",
            "company": "DocuTech Solutions",
            "salary_min": 60000,
            "salary_max": 90000,
            "location": "Remote",
            "skills": ["Documentation", "API Writing", "Markdown", "Git", "Technical Communication"],
            "experience_required": "2+ years",
            "work_mode": "remote",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 9,
            "view_count": 108
        },
        {
            "title": "Database Administrator",
            "description": "Looking for a DBA to manage and maintain our database systems and ensure optimal performance.",
            "company": "Data Systems Ltd",
            "salary_min": 85000,
            "salary_max": 125000,
            "location": "Dallas, TX",
            "skills": ["SQL", "MySQL", "PostgreSQL", "MongoDB", "Performance Tuning"],
            "experience_required": "4+ years",
            "work_mode": "onsite",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 8,
            "view_count": 97
        },
        {
            "title": "Business Analyst",
            "description": "Seeking a business analyst to bridge the gap between business needs and technical solutions.",
            "company": "Business Insights Co",
            "salary_min": 75000,
            "salary_max": 105000,
            "location": "Philadelphia, PA",
            "skills": ["Requirements Analysis", "Process Modeling", "SQL", "Stakeholder Management"],
            "experience_required": "3+ years",
            "work_mode": "hybrid",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 14,
            "view_count": 135
        },
        {
            "title": "System Administrator",
            "description": "We need a system administrator to manage our IT infrastructure and ensure system reliability.",
            "company": "IT Support Pro",
            "salary_min": 65000,
            "salary_max": 95000,
            "location": "Phoenix, AZ",
            "skills": ["Linux", "Windows Server", "Networking", "Security", "Troubleshooting"],
            "experience_required": "3+ years",
            "work_mode": "onsite",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 7,
            "view_count": 89
        },
        {
            "title": "AI Research Scientist",
            "description": "Looking for an AI research scientist to conduct cutting-edge research in artificial intelligence and machine learning.",
            "company": "Future AI Lab",
            "salary_min": 130000,
            "salary_max": 170000,
            "location": "Cambridge, MA",
            "skills": ["Machine Learning", "Research", "Python", "Deep Learning", "Mathematics"],
            "experience_required": "5+ years",
            "work_mode": "hybrid",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 23,
            "view_count": 201
        },
        {
            "title": "Network Engineer",
            "description": "Seeking a network engineer to design, implement, and maintain our network infrastructure.",
            "company": "Network Solutions Inc",
            "salary_min": 80000,
            "salary_max": 115000,
            "location": "Remote",
            "skills": ["Networking", "Cisco", "Routing", "Switching", "VPN"],
            "experience_required": "4+ years",
            "work_mode": "remote",
            "posted_date": datetime.now(),
            "is_active": True,
            "application_count": 10,
            "view_count": 118
        }
    ]
    
    try:
        # Clear existing sample jobs
        await jobs_collection.delete_many({"title": {"$in": [
            "Senior Software Engineer", 
            "Product Manager", 
            "Data Scientist",
            "Frontend Developer",
            "DevOps Engineer",
            "UX/UI Designer",
            "Backend Developer",
            "Cybersecurity Analyst",
            "Machine Learning Engineer",
            "Full Stack Developer",
            "Mobile App Developer",
            "Data Analyst",
            "Cloud Solutions Architect",
            "QA Engineer",
            "Technical Writer",
            "Database Administrator",
            "Business Analyst",
            "System Administrator",
            "AI Research Scientist",
            "Network Engineer"
        ]}})
        
        # Insert sample jobs
        result = await jobs_collection.insert_many(sample_jobs)
        print(f"Successfully created {len(result.inserted_ids)} sample jobs")
        
        # Print the inserted job IDs
        for i, job_id in enumerate(result.inserted_ids):
            print(f"Job {i+1}: {job_id}")
            
    except Exception as e:
        print(f"Error creating sample jobs: {e}")

if __name__ == "__main__":
    asyncio.run(create_sample_jobs())