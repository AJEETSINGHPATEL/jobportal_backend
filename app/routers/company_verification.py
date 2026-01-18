from fastapi import APIRouter, HTTPException, status, Depends
from app.models.company_verification import CompanyVerificationCreate, CompanyVerificationUpdate, CompanyVerification
from app.models.user import UserRole
from app.database.database import company_verifications_collection, companies_collection, users_collection
from bson import ObjectId
from datetime import datetime
from typing import List

router = APIRouter(prefix="/api/company-verification", tags=["Company Verification"])

async def get_current_user_role(user_id: str) -> str:
    """Helper function to get user role"""
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.get("role", "job_seeker")

@router.post("/", response_model=CompanyVerification)
async def create_company_verification(verification: CompanyVerificationCreate):
    try:
        # Check if company exists
        company = await companies_collection.find_one({"_id": ObjectId(verification.company_id)})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Check if user owns the company
        if str(company.get("owner_id")) != verification.owner_id:
            raise HTTPException(status_code=403, detail="You don't have permission to verify this company")
        
        # Check if verification already exists for this company
        existing_verification = await company_verifications_collection.find_one({
            "company_id": verification.company_id
        })
        if existing_verification:
            raise HTTPException(status_code=400, detail="Verification request already exists for this company")
        
        # Convert to dict and add required fields
        verification_dict = verification.dict()
        verification_dict["created_at"] = datetime.now()
        verification_dict["updated_at"] = datetime.now()
        
        result = await company_verifications_collection.insert_one(verification_dict)
        verification_dict["id"] = str(result.inserted_id)
        del verification_dict["_id"]
        
        return CompanyVerification(**verification_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating verification request: {str(e)}")

@router.get("/{verification_id}", response_model=CompanyVerification)
async def get_company_verification(verification_id: str):
    try:
        verification = await company_verifications_collection.find_one({"_id": ObjectId(verification_id)})
        if not verification:
            raise HTTPException(status_code=404, detail="Verification request not found")
        
        verification["id"] = str(verification["_id"])
        del verification["_id"]
        
        # Get company details
        company = await companies_collection.find_one({"_id": ObjectId(verification["company_id"])})
        if company:
            verification["company_name"] = company.get("name", "Unknown Company")
        
        return CompanyVerification(**verification)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving verification: {str(e)}")

@router.put("/{verification_id}", response_model=CompanyVerification)
async def update_company_verification(verification_id: str, verification_update: CompanyVerificationUpdate, current_user_id: str = None):
    try:
        # Get existing verification
        existing_verification = await company_verifications_collection.find_one({"_id": ObjectId(verification_id)})
        if not existing_verification:
            raise HTTPException(status_code=404, detail="Verification request not found")
        
        # Check if user is admin to approve/reject verification
        if current_user_id:
            user_role = await get_current_user_role(current_user_id)
            if user_role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="Only admins can update verification status")
        
        # Prepare update data
        update_data = verification_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
        
        # If status is being updated, add verified_by field
        if "verification_status" in update_data:
            if current_user_id:
                update_data["verified_by"] = current_user_id
        
        await company_verifications_collection.update_one(
            {"_id": ObjectId(verification_id)}, 
            {"$set": update_data}
        )
        
        # Get updated verification
        updated_verification = await company_verifications_collection.find_one({"_id": ObjectId(verification_id)})
        if updated_verification:
            updated_verification["id"] = str(updated_verification["_id"])
            del updated_verification["_id"]
            
            # Get company details
            company = await companies_collection.find_one({"_id": ObjectId(updated_verification["company_id"])})
            if company:
                updated_verification["company_name"] = company.get("name", "Unknown Company")
            
            return CompanyVerification(**updated_verification)
        else:
            raise HTTPException(status_code=404, detail="Verification not found after update")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating verification: {str(e)}")

@router.get("/", response_model=List[CompanyVerification])
async def list_company_verifications(
    status: str = None,
    skip: int = 0,
    limit: int = 20,
    current_user_id: str = None
):
    try:
        # Check if user is admin
        if current_user_id:
            user_role = await get_current_user_role(current_user_id)
            if user_role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="Only admins can view all verification requests")
        
        query = {}
        if status:
            query["verification_status"] = status
        
        verifications = []
        cursor = company_verifications_collection.find(query).skip(skip).limit(limit)
        async for verification in cursor:
            verification["id"] = str(verification["_id"])
            del verification["_id"]
            
            # Get company details
            company = await companies_collection.find_one({"_id": ObjectId(verification["company_id"])})
            if company:
                verification["company_name"] = company.get("name", "Unknown Company")
            
            verifications.append(CompanyVerification(**verification))
        
        return verifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing verifications: {str(e)}")

@router.delete("/{verification_id}")
async def delete_company_verification(verification_id: str, current_user_id: str = None):
    try:
        # Check if user is admin
        if current_user_id:
            user_role = await get_current_user_role(current_user_id)
            if user_role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="Only admins can delete verification requests")
        
        verification = await company_verifications_collection.find_one({"_id": ObjectId(verification_id)})
        if not verification:
            raise HTTPException(status_code=404, detail="Verification request not found")
        
        await company_verifications_collection.delete_one({"_id": ObjectId(verification_id)})
        return {"message": "Verification request deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting verification: {str(e)}")