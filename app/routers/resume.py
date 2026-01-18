from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from typing import List
import uuid
from datetime import datetime, timezone
import os
from pathlib import Path
from bson import ObjectId
from fastapi.responses import FileResponse
from app.models.resume import ResumeCreate, ResumeUpdate, ResumeInDB
from app.utils.ai_service import ai_service
from app.utils.auth import get_current_user
from fastapi.security import OAuth2PasswordBearer
from app.database.database import get_resumes_collection, get_users_collection
import io

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/api/resume", tags=["Resume"])

# Create uploads directory if it doesn't exist
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

# Database collection will be accessed via get_resumes_collection()

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        import PyPDF2
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF file: {str(e)}")

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        from docx import Document
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading DOCX file: {str(e)}")

def extract_text_from_doc(file_content: bytes) -> str:
    """Extract text from DOC file (simplified approach)"""
    # For DOC files, we'll need to use a different library like python-docx2txt
    # For now, we'll return a placeholder since python-docx doesn't support .doc files
    raise HTTPException(status_code=400, detail="DOC file format not supported, please convert to DOCX or PDF")

@router.post("/upload", response_model=ResumeInDB)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    token: str = Depends(oauth2_scheme)
):
    try:
        current_user = await get_current_user(token)
    except Exception as e:
        print(f"Authentication error: {str(e)}")  # Debug logging
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Ensure the user is uploading for themselves
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload resume for another user"
        )
    
    # Upload a resume file
    try:
        # Validate file type
        allowed_types = ["application/pdf", "application/msword", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        print(f"Uploaded file content type: {file.content_type}")  # Debug line
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, DOC, and DOCX files are allowed.")
        
        # Validate file size (max 5MB)
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 5MB.")
        
        # Create resume record
        resume_id = str(uuid.uuid4())
        
        # Prepare resume data with explicit handling
        file_name = getattr(file, 'filename', 'untitled')
        file_size = len(contents)
        file_type = getattr(file, 'content_type', 'application/octet-stream') or 'application/octet-stream'
        
        print(f"Creating resume record - user_id: {user_id}, filename: {file_name}, size: {file_size}, type: {file_type}")  # Debug line
        
        try:
            resume_data = ResumeCreate(
                user_id=user_id,
                file_name=file_name,
                file_size=file_size,
                file_type=file_type
            )
            print(f"Resume data created successfully: {resume_data}")  # Debug line
        except Exception as e:
            print(f"Error creating ResumeCreate object: {str(e)}")  # Debug line
            raise HTTPException(status_code=422, detail=f"Validation error creating resume: {str(e)}")
        
        # Save file to uploads directory
        file_extension = Path(file.filename).suffix
        file_path = UPLOADS_DIR / f"{resume_id}{file_extension}"
        
        # Ensure the uploads directory exists
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Store in database
        resume_dict = resume_data.dict()
        resume_dict["_id"] = resume_id  # Use _id for MongoDB
        resume_dict["uploaded_at"] = datetime.now(timezone.utc)  # Updated to use timezone-aware datetime
        resume_dict["file_path"] = str(file_path)  # Store the file path
        resume_dict["resume_url"] = f"/api/resume/download/{resume_id}"  # Create a download URL
        
        # Get resumes collection
        resumes_collection = get_resumes_collection()
        
        # Insert the resume document
        result = await resumes_collection.insert_one(resume_dict)
        
        # Update the user's resume_url field in the users collection
        users_collection = get_users_collection()
        await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"resume_url": f"/api/resume/download/{resume_id}"}}
        )
        
        # Return the created resume
        resume_dict["id"] = resume_id  # Add id field for response
        return ResumeInDB(**resume_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{resume_id}")
async def download_resume(resume_id: str, token: str = Depends(oauth2_scheme)):
    """Download a resume file"""
    try:
        current_user = await get_current_user(token)
        
        # Get resumes collection
        resumes_collection = get_resumes_collection()
        
        # Find the resume
        resume = await resumes_collection.find_one({"_id": resume_id})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Check if user owns this resume
        if resume["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this resume"
            )
        
        # Get the file path
        file_path = Path(resume["file_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Resume file not found")
        
        return FileResponse(
            path=file_path,
            filename=resume["file_name"],
            media_type=resume["file_type"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/{resume_id}", response_model=dict)
async def analyze_resume_endpoint(resume_id: str, token: str = Depends(oauth2_scheme)):
    """Analyze a resume for ATS compatibility"""
    try:
        current_user = await get_current_user(token)
        
        # Get resumes collection
        resumes_collection = get_resumes_collection()
        
        # Find the resume
        resume_record = await resumes_collection.find_one({"_id": resume_id})
        if not resume_record:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Check if user owns this resume
        if resume_record["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to analyze this resume"
            )
        
        # Read file content from the stored file path
        file_path = Path(resume_record["file_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Resume file not found")
        
        content_type = resume_record["file_type"]
        
        # Read file content
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # Extract text based on file type
        if content_type == "application/pdf":
            resume_text = extract_text_from_pdf(file_content)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            resume_text = extract_text_from_docx(file_content)
        elif content_type == "application/msword":
            resume_text = extract_text_from_doc(file_content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the resume file")
        
        # Analyze resume using AI service
        analysis_result = ai_service.analyze_resume(resume_text)
        
        # Update resume with analysis results in the database
        update_data = {
            "ats_score": analysis_result.get("ats_score", 0),
            "skills": analysis_result.get("skills", []),
            "experience_years": analysis_result.get("experience_years", 0),
            "achievements": analysis_result.get("achievements", []),
            "improvements": analysis_result.get("improvements", []),
            "analyzed_at": datetime.now(timezone.utc)  # Updated to use timezone-aware datetime
        }
        
        await resumes_collection.update_one(
            {"_id": resume_id},
            {"$set": update_data}
        )
        
        # Update the local record for response
        resume_record.update(update_data)
        
        return {
            "resume_id": resume_id,
            "analysis": analysis_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{resume_id}", response_model=ResumeInDB)
async def get_resume_endpoint(resume_id: str, token: str = Depends(oauth2_scheme)):
    """Get resume by ID"""
    try:
        current_user = await get_current_user(token)
        
        # Get resumes collection
        resumes_collection = get_resumes_collection()
        
        # Find the resume
        resume = await resumes_collection.find_one({"_id": resume_id})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Check if user owns this resume
        if resume["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this resume"
            )
        
        # Prepare the resume data for response
        resume["id"] = resume["_id"]  # Use id instead of _id for the response
        del resume["_id"]  # Remove _id since we're using id
        
        # Remove file_content from the response to avoid sending large data
        if "file_content" in resume:
            del resume["file_content"]
        
        return ResumeInDB(**resume)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}", response_model=List[ResumeInDB])
async def get_user_resumes_endpoint(user_id: str, token: str = Depends(oauth2_scheme)):
    """Get all resumes for a user"""
    try:
        current_user = await get_current_user(token)
        
        # Only allow users to access their own resumes
        if current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access these resumes"
            )
        
        # Get resumes collection
        resumes_collection = get_resumes_collection()
        
        user_resumes = []
        
        # Find all resumes for the user
        cursor = resumes_collection.find({"user_id": user_id})
        async for resume in cursor:
            # Prepare the resume data for response
            resume["id"] = str(resume["_id"])  # Use id instead of _id for the response and ensure it's a string
            del resume["_id"]  # Remove _id since we're using id
            
            # Remove file_content from the response to avoid sending large data
            if "file_content" in resume:
                del resume["file_content"]
            
            # Create ResumeInDB object with proper validation
            try:
                resume_obj = ResumeInDB(**resume)
                user_resumes.append(resume_obj)
            except Exception as validation_error:
                print(f"Error validating resume data: {validation_error}")
                continue  # Skip invalid resumes
        
        return user_resumes
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_user_resumes_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching resumes: {str(e)}")

@router.put("/{resume_id}", response_model=ResumeInDB)
async def update_resume_endpoint(resume_id: str, resume_update: ResumeUpdate, token: str = Depends(oauth2_scheme)):
    """Update resume information"""
    try:
        current_user = await get_current_user(token)
        
        # Get resumes collection
        resumes_collection = get_resumes_collection()
        
        # Find the resume
        resume = await resumes_collection.find_one({"_id": resume_id})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Check if user owns this resume
        if resume["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this resume"
            )
        
        # Prepare update data
        update_data = {}
        for field, value in resume_update.dict().items():
            if value is not None:
                update_data[field] = value
        
        # Update the resume in the database
        await resumes_collection.update_one(
            {"_id": resume_id},
            {"$set": update_data}
        )
        
        # Get the updated resume for response
        updated_resume = await resumes_collection.find_one({"_id": resume_id})
        updated_resume["id"] = updated_resume["_id"]  # Use id instead of _id for the response
        del updated_resume["_id"]  # Remove _id since we're using id
        
        # Remove file_content from the response
        if "file_content" in updated_resume:
            del updated_resume["file_content"]
        
        return ResumeInDB(**updated_resume)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{resume_id}")
async def delete_resume_endpoint(resume_id: str, token: str = Depends(oauth2_scheme)):
    """Delete a resume"""
    try:
        current_user = await get_current_user(token)
        
        # Get resumes collection
        resumes_collection = get_resumes_collection()
        
        # Find the resume
        resume = await resumes_collection.find_one({"_id": resume_id})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Check if user owns this resume
        if resume["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this resume"
            )
        
        # Also delete the physical file
        file_path = Path(resume["file_path"])
        if file_path.exists():
            os.remove(file_path)
        
        # Delete from database
        await resumes_collection.delete_one({"_id": resume_id})
        
        return {"message": "Resume deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/all", response_model=List[ResumeInDB])
async def get_all_resumes_admin(token: str = Depends(oauth2_scheme)):
    """Get all resumes for admin users"""
    try:
        current_user = await get_current_user(token)
        
        # Check if user is admin
        from app.utils.auth import get_current_user_role
        from app.models.user import UserRole
        user_role = await get_current_user_role(current_user["id"])
        if user_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can access this resource"
            )
        
        # Get resumes collection
        resumes_collection = get_resumes_collection()
        
        all_resumes = []
        
        # Find all resumes
        async for resume in resumes_collection.find({}):
            # Prepare the resume data for response
            resume["id"] = resume["_id"]  # Use id instead of _id for the response
            del resume["_id"]  # Remove _id since we're using id
            
            # Remove file_content from the response to avoid sending large data
            if "file_content" in resume:
                del resume["file_content"]
            
            all_resumes.append(ResumeInDB(**resume))
        
        return all_resumes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))