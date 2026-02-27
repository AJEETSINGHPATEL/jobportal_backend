from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from app.models.company import CompanyCreate, CompanyUpdate, Company as CompanySchema
from app.database.database import get_db
from app.database.models import Company as CompanyModel
from app.utils.auth import get_current_user
from typing import List
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/companies", tags=["Companies"])

@router.post("/", response_model=CompanySchema)
async def create_company(
    company: CompanyCreate,
    token: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user = token
    # Only employers can create companies
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can create companies"
        )
    
    # Check if company already exists
    stmt = select(CompanyModel).where(CompanyModel.name == company.name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company with this name already exists"
        )
    
    # Create company
    db_company = CompanyModel(
        id=str(uuid.uuid4()),
        **company.model_dump(),
        created_by=current_user["id"],
        verification_status="pending",  # Default status
        is_verified=False,  # Default value
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    
    return db_company

@router.get("/", response_model=List[CompanySchema])
async def get_companies(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CompanyModel).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{company_id}", response_model=CompanySchema)
async def get_company(company_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CompanyModel).where(CompanyModel.id == company_id)
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    return company

@router.put("/{company_id}", response_model=CompanySchema)
async def update_company(
    company_id: str,
    company_update: CompanyUpdate,
    token: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user = token
    
    stmt = select(CompanyModel).where(CompanyModel.id == company_id)
    result = await db.execute(stmt)
    db_company = result.scalar_one_or_none()
    
    if not db_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
        
    # Check if user is authorized to update (owner or admin)
    if db_company.created_by != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this company"
        )
    
    # Prepare update data
    update_data = company_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_company, key, value)
    
    db_company.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_company)
    return db_company
