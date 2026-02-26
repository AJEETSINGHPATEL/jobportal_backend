from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, delete
from app.models.resume import ResumeCreate, ResumeUpdate, ResumeInDB
from app.database.database import get_db
from app.database.models import Resume as ResumeModel, User as UserModel
from app.utils.auth import get_current_user
from app.utils.ai_service import ai_service
from fastapi.responses import FileResponse
from typing import List
import uuid
from datetime import datetime, timezone
import os
from pathlib import Path
import io

router = APIRouter(prefix="/api/resume", tags=["Resume"])

# Create uploads directory if it doesn't exist
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

def extract_text_from_pdf(file_content: bytes) -> str:
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
    try:
        from docx import Document
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading DOCX file: {str(e)}")

@router.post("/upload", response_model=ResumeInDB)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to upload resume for another user")
    
    try:
        allowed_types = ["application/pdf", "application/msword", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, DOC, and DOCX files are allowed.")
        
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 5MB.")
        
        resume_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        file_path = UPLOADS_DIR / f"{resume_id}{file_extension}"
        
        with open(file_path, "wb") as f:
            f.write(contents)
            
        resume_url = f"/api/resume/download/{resume_id}"
        
        db_resume = ResumeModel(
            id=resume_id,
            user_id=user_id,
            file_name=file.filename,
            file_path=str(file_path),
            file_size=len(contents),
            file_type=file.content_type,
            resume_url=resume_url,
            uploaded_at=datetime.utcnow()
        )
        
        db.add(db_resume)
        
        # Update user's resume_url
        user_update_stmt = update(UserModel).where(UserModel.id == user_id).values(resume_url=resume_url)
        await db.execute(user_update_stmt)
        
        await db.commit()
        await db.refresh(db_resume)
        return db_resume
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{resume_id}")
async def download_resume(resume_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    if resume.user_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    file_path = Path(resume.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(path=file_path, filename=resume.file_name, media_type=resume.file_type)

@router.post("/analyze/{resume_id}", response_model=dict)
async def analyze_resume_endpoint(resume_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
    result = await db.execute(stmt)
    db_resume = result.scalar_one_or_none()
    
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    if db_resume.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    file_path = Path(db_resume.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    with open(file_path, "rb") as f:
        file_content = f.read()
        
    if db_resume.file_type == "application/pdf":
        resume_text = extract_text_from_pdf(file_content)
    elif db_resume.file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        resume_text = extract_text_from_docx(file_content)
    else:
        raise HTTPException(status_code=400, detail="Conversion for this file type is not supported yet")
        
    analysis_result = ai_service.analyze_resume(resume_text)
    
    db_resume.ats_score = analysis_result.get("ats_score", 0)
    db_resume.skills = analysis_result.get("skills", [])
    db_resume.experience_years = analysis_result.get("experience_years", 0)
    db_resume.achievements = analysis_result.get("achievements", [])
    db_resume.improvements = analysis_result.get("improvements", [])
    db_resume.analyzed_at = datetime.utcnow()
    
    await db.commit()
    return {"resume_id": resume_id, "analysis": analysis_result}

@router.get("/{resume_id}", response_model=ResumeInDB)
async def get_resume_endpoint(resume_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    if resume.user_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    return resume

@router.get("/user/{user_id}", response_model=List[ResumeInDB])
async def get_user_resumes_endpoint(user_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user["id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    stmt = select(ResumeModel).where(ResumeModel.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/{resume_id}", response_model=ResumeInDB)
async def update_resume_endpoint(resume_id: str, resume_update: ResumeUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
    result = await db.execute(stmt)
    db_resume = result.scalar_one_or_none()
    
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    if db_resume.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    update_data = resume_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_resume, key, value)
        
    await db.commit()
    await db.refresh(db_resume)
    return db_resume

@router.delete("/{resume_id}")
async def delete_resume_endpoint(resume_id: str, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
    result = await db.execute(stmt)
    db_resume = result.scalar_one_or_none()
    
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    if db_resume.user_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if db_resume.file_path:
        file_path = Path(db_resume.file_path)
        if file_path.exists():
            os.remove(file_path)
            
    await db.delete(db_resume)
    await db.commit()
    return {"message": "Resume deleted successfully"}

@router.get("/admin/all", response_model=List[ResumeInDB])
async def get_all_resumes_admin(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    stmt = select(ResumeModel)
    result = await db.execute(stmt)
    return result.scalars().all()
