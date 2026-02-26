from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from app.utils.ai_service import get_ai_response, ai_service
from app.utils.job_search_service import job_search_service
from app.database.database import get_db
from app.database.models import ActivityLog, RecruiterProfile, Company, User, ChatHistory
from app.utils.auth import get_current_user, get_optional_user
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/ai", tags=["AI Services"])

class ChatMessage(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

class JobSearchRequest(BaseModel):
    query: str
    location: str = ""
    job_type: str = ""

class JobSearchResponse(BaseModel):
    jobs: List[Dict[str, Any]]
    message: str

class EmployerContactRequest(BaseModel):
    company_id: str

class EmployerContactResponse(BaseModel):
    contact_info: Optional[Dict[str, Any]]
    message: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_message: ChatMessage, 
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Chat with AI assistant
    """
    try:
        # Extract intent if user is authenticated
        intent = "General Inquiry"
        session_id = chat_message.session_id or str(uuid.uuid4())
        
        if current_user:
            intent = await ai_service.extract_intent(chat_message.message)
            
            # Save user message to ChatHistory
            user_msg = ChatHistory(
                id=str(uuid.uuid4()),
                user_id=current_user["id"],
                session_id=session_id,
                role="user",
                content=chat_message.message,
                intent=intent,
                created_at=datetime.utcnow()
            )
            db.add(user_msg)

        # Get AI response
        response = await get_ai_response(
            chat_message.message, 
            chat_message.history,
            current_user
        )
        
        # Log the interaction and save assistant message if user is authenticated
        if current_user:
            try:
                # Save assistant response to ChatHistory
                assistant_msg = ChatHistory(
                    id=str(uuid.uuid4()),
                    user_id=current_user["id"],
                    session_id=session_id,
                    role="assistant",
                    content=response,
                    intent=intent,
                    created_at=datetime.utcnow()
                )
                db.add(assistant_msg)

                new_activity = ActivityLog(
                    id=str(uuid.uuid4()),
                    user_id=current_user["id"],
                    activity_type='ai_chat',
                    activity_metadata={
                        'message': chat_message.message,
                        'response_length': len(response),
                        'intent': intent,
                        'session_id': session_id
                    },
                    created_at=datetime.utcnow()
                )
                db.add(new_activity)
                await db.commit()
            except Exception as e:
                print(f"Error logging activity: {e}")
                await db.rollback()
        
        return ChatResponse(response=response)
        
    except Exception as e:
        if current_user:
            await db.rollback()
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@router.get("/knowledge-base", response_model=List[Dict[str, Any]])
async def get_knowledge_base(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve user chat knowledge base (intents and summaries)
    """
    try:
        # Get unique intents and latest messages for the user
        stmt = select(ChatHistory).where(
            ChatHistory.user_id == current_user["id"],
            ChatHistory.role == "user"
        ).order_by(ChatHistory.created_at.desc())
        
        result = await db.execute(stmt)
        histories = result.scalars().all()
        
        # Group by intent/session or just return recent ones
        knowledge = []
        seen_intents = set()
        
        for h in histories:
            if h.intent not in seen_intents or len(seen_intents) < 10:
                knowledge.append({
                    "id": h.id,
                    "session_id": h.session_id,
                    "intent": h.intent,
                    "content": h.content,
                    "created_at": h.created_at
                })
                seen_intents.add(h.intent)
        
        return knowledge
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving knowledge base: {str(e)}")

@router.post("/search-jobs", response_model=JobSearchResponse)
async def search_jobs_api(job_request: JobSearchRequest):
    """
    Search for jobs using the job search service
    """
    try:
        jobs = await job_search_service.search_real_jobs(
            query=job_request.query,
            location=job_request.location,
            job_type=job_request.job_type
        )
        
        return JobSearchResponse(
            jobs=jobs,
            message=f"Found {len(jobs)} jobs matching your search criteria"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job search error: {str(e)}")

@router.post("/employer-contact", response_model=EmployerContactResponse)
async def get_employer_contact(
    contact_request: EmployerContactRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get employer contact information from PostgreSQL
    """
    try:
        # Query RecruiterProfile or Company joined with User
        stmt = select(RecruiterProfile, User.full_name, User.email, User.mobile)\
            .join(User, RecruiterProfile.user_id == User.id)\
            .where(RecruiterProfile.company_id == contact_request.company_id)
            
        result = await db.execute(stmt)
        row = result.first()
        
        if row:
            profile, full_name, email, mobile = row
            contact_info = {
                "companyId": profile.company_id,
                "companyName": profile.company_name,
                "hrName": full_name,
                "phone": mobile,
                "email": email,
                "website": profile.company_website
            }
            return EmployerContactResponse(
                contact_info=contact_info,
                message="Employer contact information retrieved successfully"
            )
        else:
            return EmployerContactResponse(
                contact_info=None,
                message="Employer contact information not found"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving employer contact: {str(e)}")

@router.get("/employer-contacts")
async def get_all_employer_contacts(db: AsyncSession = Depends(get_db)):
    """
    Get all employer contacts from PostgreSQL
    """
    try:
        stmt = select(RecruiterProfile, User.full_name, User.email, User.mobile)\
            .join(User, RecruiterProfile.user_id == User.id)
            
        result = await db.execute(stmt)
        contacts = []
        for profile, full_name, email, mobile in result.all():
            contacts.append({
                "companyId": profile.company_id or profile.id,
                "companyName": profile.company_name or "Unknown Company",
                "hrName": full_name,
                "phone": mobile,
                "email": email,
                "website": profile.company_website
            })
        
        return {"contacts": contacts, "message": "All employer contacts retrieved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving employer contacts: {str(e)}")

# Health check endpoint
@router.get("/health")
async def ai_health_check(db: AsyncSession = Depends(get_db)):
    """Check AI service health"""
    try:
        # Simple query to test DB connection
        await db.execute(select(1))
        
        return {
            "status": "healthy",
            "database": "connected",
            "ai_service": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
