from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from app.models.company import CompanyCreate, CompanyUpdate, Company
from app.database.database import get_companies_collection
from app.utils.auth import get_current_user
from bson import ObjectId
from typing import List
import datetime

router = APIRouter(prefix="/api/companies", tags=["Companies"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/", response_model=Company)
async def create_company(
    company: CompanyCreate,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Only employers can create companies
    if current_user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can create companies"
        )
    
    # Get collection in the current request context
    companies_collection = get_companies_collection()
    
    # Check if company already exists
    existing_company = await companies_collection.find_one({"name": company.name})
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company with this name already exists"
        )
    
    # Create company
    company_dict = company.dict()
    company_dict["created_by"] = current_user["id"]
    company_dict["verification_status"] = "pending"  # Default status
    company_dict["is_verified"] = False  # Default value
    company_dict["created_at"] = datetime.datetime.utcnow()
    company_dict["updated_at"] = datetime.datetime.utcnow()
    
    result = await companies_collection.insert_one(company_dict)
    company_dict["id"] = str(result.inserted_id)
    
    return Company(**company_dict)

@router.get("/", response_model=List[Company])
async def get_companies(
    skip: int = 0,
    limit: int = 20
):
    # Get collection in the current request context
    companies_collection = get_companies_collection()
    
    companies = []
    async for company in companies_collection.find().skip(skip).limit(limit):
        company["id"] = str(company["_id"])
        del company["_id"]
        companies.append(Company(**company))
    
    return companies

@router.get("/{company_id}", response_model=Company)
async def get_company(company_id: str):
    # Get collection in the current request context
    companies_collection = get_companies_collection()
    
    try:
        company = await companies_collection.find_one({"_id": ObjectId(company_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid company ID"
        )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    company["id"] = str(company["_id"])
    del company["_id"]
    
    return Company(**company)

@router.put("/{company_id}", response_model=Company)
async def update_company(
    company_id: str,
    company_update: CompanyUpdate,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(token)
    
    # Get collection in the current request context
    companies_collection = get_companies_collection()
    
    try:
        # Find the company first
        company = await companies_collection.find_one({"_id": ObjectId(company_id)})
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # Check if user is authorized to update (owner or admin)
        if company["created_by"] != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this company"
            )
        
        # Prepare update data
        update_data = company_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.datetime.utcnow()
        
        # Update the company
        result = await companies_collection.update_one(
            {"_id": ObjectId(company_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes made to company"
            )
        
        # Return updated company
        updated_company = await companies_collection.find_one({"_id": ObjectId(company_id)})
        if updated_company:
            updated_company["id"] = str(updated_company["_id"])
            del updated_company["_id"]
            return Company(**updated_company)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid company ID"
        )