from fastapi import APIRouter, HTTPException, UploadFile, Form, File
from pydantic import BaseModel
from typing import List, Optional
from app.utils.ai_service import ai_service

router = APIRouter(prefix="/api/ai", tags=["AI Services"])

class ResumeAnalysisRequest(BaseModel):
    resume_text: str

class CoverLetterRequest(BaseModel):
    job_description: str
    resume_text: str

class JobDescriptionRequest(BaseModel):
    job_title: str
    requirements: List[str]

class SkillExtractionRequest(BaseModel):
    text: str

class MatchScoreRequest(BaseModel):
    resume_skills: List[str]
    job_skills: List[str]

class InterviewQuestionsRequest(BaseModel):
    job_description: str
    resume_text: str

class InterviewAnswerRequest(BaseModel):
    question: str
    job_description: str
    resume_text: str

class ResumeAnalysisResponse(BaseModel):
    skills: List[str]
    experience_years: int
    achievements: List[str]
    improvements: List[str]
    ats_score: int

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []

@router.post("/chat", response_model=dict)
async def chat(request: ChatRequest):
    try:
        response = ai_service.chat(request.message, request.history)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume-analyze", response_model=dict)
async def analyze_resume(request: ResumeAnalysisRequest):
    try:
        result = ai_service.analyze_resume(request.resume_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume-analyze-file", response_model=dict)
async def analyze_resume_file(file: UploadFile = File(...)):
    try:
        # Read the file content
        file_content = await file.read()
        
        # Check if content type is available
        content_type = file.content_type or 'application/octet-stream'
        
        # Extract text from the file based on its type
        resume_text = ai_service.extract_text_from_file(file_content, content_type)
        
        # Analyze the extracted text
        result = ai_service.analyze_resume(resume_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cover-letter", response_model=dict)
async def generate_cover_letter(request: CoverLetterRequest):
    try:
        result = ai_service.generate_cover_letter(
            request.job_description, 
            request.resume_text
        )
        return {"cover_letter": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cover-letter-file", response_model=dict)
async def generate_cover_letter_file(job_description: str = Form(...), file: UploadFile = File(...)):
    try:
        # Read the file content
        file_content = await file.read()
        
        # Check if content type is available
        content_type = file.content_type or 'application/octet-stream'
        
        # Extract text from the file based on its type
        resume_text = ai_service.extract_text_from_file(file_content, content_type)
        
        # Generate cover letter using the extracted text
        cover_letter = ai_service.generate_cover_letter(job_description, resume_text)
        return {"cover_letter": cover_letter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/job-description", response_model=dict)
async def generate_job_description(request: JobDescriptionRequest):
    try:
        result = ai_service.generate_job_description(
            request.job_title, 
            request.requirements
        )
        return {"job_description": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-skills", response_model=dict)
async def extract_skills(request: SkillExtractionRequest):
    try:
        result = ai_service.extract_skills(request.text)
        return {"skills": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/match-score", response_model=dict)
async def calculate_match_score(request: MatchScoreRequest):
    try:
        score = ai_service.calculate_match_score(
            request.resume_skills, 
            request.job_skills
        )
        return {"match_score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interview-questions", response_model=dict)
async def generate_interview_questions(request: InterviewQuestionsRequest):
    try:
        result = ai_service.generate_interview_questions(
            request.job_description, 
            request.resume_text
        )
        return {"questions": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interview-questions-file", response_model=dict)
async def generate_interview_questions_file(job_description: str = Form(...), file: UploadFile = File(...)):
    try:
        # Read the file content
        file_content = await file.read()
        
        # Check if content type is available
        content_type = file.content_type or 'application/octet-stream'
        
        # Extract text from the file based on its type
        resume_text = ai_service.extract_text_from_file(file_content, content_type)
        
        # Generate interview questions using the extracted text
        questions = ai_service.generate_interview_questions(job_description, resume_text)
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interview-answer", response_model=dict)
async def generate_interview_answer(request: InterviewAnswerRequest):
    try:
        result = ai_service.generate_interview_answer(
            request.question,
            request.job_description,
            request.resume_text
        )
        return {"answer": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))