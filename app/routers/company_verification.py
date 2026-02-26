from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from app.database.database import get_db
from app.database.models import CompanyVerification as CompanyVerificationModel, Company as CompanyModel, User as UserModel
from app.models.company_verification import CompanyVerificationCreate, CompanyVerificationUpdate, CompanyVerification as CompanyVerificationSchema
from app.models.user import UserRole
from app.utils.auth import get_current_user
from datetime import datetime
from typing import List
import uuid

router = APIRouter(prefix="/api/company-verification", tags=["Company Verification"])

@router.post("/", response_model=CompanyVerificationSchema)
async def create_company_verification(
    verification: CompanyVerificationCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if company exists
        company_stmt = select(CompanyModel).where(CompanyModel.id == verification.company_id)
        company = (await db.execute(company_stmt)).scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Check if user owns the company
        if company.created_by != verification.owner_id:
            raise HTTPException(status_code=403, detail="You don't have permission to verify this company")
        
        # Check if verification already exists for this company
        existing_stmt = select(CompanyVerificationModel).where(CompanyVerificationModel.company_id == verification.company_id)
        existing_verification = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing_verification:
            raise HTTPException(status_code=400, detail="Verification request already exists for this company")
        
        # Create verification record
        verification_db = CompanyVerificationModel(
            id=str(uuid.uuid4()),
            company_id=verification.company_id,
            owner_id=verification.owner_id,
            verification_documents=verification.verification_documents,
            verification_status=verification.verification_status,
            verification_notes=verification.verification_notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(verification_db)
        await db.commit()
        await db.refresh(verification_db)
        
        # Add company name for response
        verification_db.company_name = company.name
        
        return verification_db
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating verification request: {str(e)}")

@router.get("/{verification_id}", response_model=CompanyVerificationSchema)
async def get_company_verification(
    verification_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(CompanyVerificationModel, CompanyModel.name)\
            .join(CompanyModel, CompanyModel.id == CompanyVerificationModel.company_id)\
            .where(CompanyVerificationModel.id == verification_id)
        
        result = await db.execute(stmt)
        res = result.first()
        if not res:
            raise HTTPException(status_code=404, detail="Verification request not found")
        
        verification, company_name = res
        verification.company_name = company_name
        return verification
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving verification: {str(e)}")

@router.put("/{verification_id}", response_model=CompanyVerificationSchema)
async def update_company_verification(
    verification_id: str, 
    verification_update: CompanyVerificationUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check if user is admin
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admins can update verification status")
            
        # Get existing verification
        stmt = select(CompanyVerificationModel).where(CompanyVerificationModel.id == verification_id)
        verification = (await db.execute(stmt)).scalar_one_or_none()
        if not verification:
            raise HTTPException(status_code=404, detail="Verification request not found")
        
        # Update fields
        update_data = verification_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(verification, key, value)
        
        verification.updated_at = datetime.utcnow()
        
        if "verification_status" in update_data:
            verification.verified_by = current_user["id"]
        
        await db.commit()
        await db.refresh(verification)
        
        # Get company name for response
        company_stmt = select(CompanyModel.name).where(CompanyModel.id == verification.company_id)
        company_name = (await db.execute(company_stmt)).scalar()
        verification.company_name = company_name or "Unknown Company"
        
        return verification
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating verification: {str(e)}")

@router.get("/", response_model=List[CompanyVerificationSchema])
async def list_company_verifications(
    status: str = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check if user is admin
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admins can view all verification requests")
        
        stmt = select(CompanyVerificationModel, CompanyModel.name)\
            .join(CompanyModel, CompanyModel.id == CompanyVerificationModel.company_id)
            
        if status:
            stmt = stmt.where(CompanyVerificationModel.verification_status == status)
        
        stmt = stmt.offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        verifications = []
        for verification, company_name in result.all():
            verification.company_name = company_name
            verifications.append(verification)
        
        return verifications
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing verifications: {str(e)}")

@router.delete("/{verification_id}")
async def delete_company_verification(
    verification_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check if user is admin
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admins can delete verification requests")
        
        stmt = select(CompanyVerificationModel).where(CompanyVerificationModel.id == verification_id)
        verification = (await db.execute(stmt)).scalar_one_or_none()
        if not verification:
            raise HTTPException(status_code=404, detail="Verification request not found")
        
        await db.delete(verification)
        await db.commit()
        return {"message": "Verification request deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting verification: {str(e)}")
