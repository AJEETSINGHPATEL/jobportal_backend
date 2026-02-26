# Database Schema Documentation

## Collections

### users
Stores user information for job seekers, employers, and admins.

```json
{
  "_id": "ObjectId",
  "email": "String (unique)",
  "hashed_password": "String",
  "full_name": "String",
  "role": "Enum ['job_seeker', 'employer', 'admin']",
  "mobile": "String",
  "is_verified": "Boolean",
  "created_at": "DateTime",
  "updated_at": "DateTime"
}
```

### jobs
Stores job postings.

```json
{
  "_id": "ObjectId",
  "title": "String",
  "description": "String",
  "company": "String",
  "salary_min": "Number",
  "salary_max": "Number",
  "location": "String",
  "skills": "Array of Strings",
  "experience_required": "String",
  "work_mode": "String",
  "company_logo_url": "String",
  "company_rating": "Number",
  "reviews_count": "Number",
  "posted_by": "ObjectId (reference to user)",
  "posted_at": "DateTime",
  "is_active": "Boolean",
  "application_count": "Number",
  "view_count": "Number"
}
```

### applications
Stores job applications from job seekers.

```json
{
  "_id": "ObjectId",
  "job_id": "String",
  "user_id": "ObjectId",
  "status": "Enum ['applied', 'reviewed', 'interview', 'offered', 'accepted', 'rejected']",
  "cover_letter": "String",
  "resume_url": "String",
  "created_at": "DateTime",
  "updated_at": "DateTime"
}
```

### saved_jobs
Stores jobs saved by job seekers.

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "job_id": "String",
  "created_at": "DateTime"
}
```

### job_seeker_profiles
Stores detailed profiles for job seekers.

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "phone": "String",
  "skills": "Array of Strings",
  "experience_years": "Number",
  "education": "Array of Objects",
  "preferred_locations": "Array of Strings",
  "resume_url": "String",
  "profile_completion_pct": "Number",
  "created_at": "DateTime",
  "updated_at": "DateTime"
}
```

### recruiter_profiles
Stores company information for recruiters.

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "company_name": "String",
  "company_logo": "String",
  "designation": "String",
  "company_website": "String",
  "industry": "String",
  "created_at": "DateTime",
  "updated_at": "DateTime"
}
```