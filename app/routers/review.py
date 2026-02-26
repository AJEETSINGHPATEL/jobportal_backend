from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update
from app.models.review import ReviewCreate, ReviewUpdate, Review as ReviewSchema
from app.database.database import get_db
from app.database.models import Review as ReviewModel, Company as CompanyModel, User as UserModel
from datetime import datetime
from typing import List
import uuid

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])

@router.post("/", response_model=ReviewSchema)
async def create_review(review: ReviewCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Check if company exists
        comp_stmt = select(CompanyModel).where(CompanyModel.id == review.company_id)
        comp_result = await db.execute(comp_stmt)
        if not comp_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Check if user exists
        user_stmt = select(UserModel).where(UserModel.id == review.user_id)
        user_result = await db.execute(user_stmt)
        if not user_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has already reviewed this company
        exist_stmt = select(ReviewModel).where(
            and_(
                ReviewModel.company_id == review.company_id,
                ReviewModel.user_id == review.user_id
            )
        )
        exist_result = await db.execute(exist_stmt)
        if exist_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="You have already reviewed this company")
        
        # Validate ratings are between 1-5
        for r_name, r_val in [
            ("Work culture", review.rating_work_culture),
            ("Salary", review.rating_salary),
            ("HR", review.rating_hr),
            ("Management", review.rating_management)
        ]:
            if not 1 <= r_val <= 5:
                raise HTTPException(status_code=400, detail=f"{r_name} rating must be between 1 and 5")
        
        # Create review
        db_review = ReviewModel(
            id=str(uuid.uuid4()),
            **review.model_dump(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_review)
        await db.commit()
        await db.refresh(db_review)
        
        return db_review
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating review: {str(e)}")

@router.get("/{review_id}", response_model=ReviewSchema)
async def get_review(review_id: str, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(ReviewModel, CompanyModel.name.label("company_name"), UserModel.full_name.label("user_name"))\
            .join(CompanyModel, ReviewModel.company_id == CompanyModel.id)\
            .join(UserModel, ReviewModel.user_id == UserModel.id)\
            .where(ReviewModel.id == review_id)
            
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Review not found")
        
        review, company_name, user_name = row
        # Pydantic will handle field mapping if names match or are injected
        # For simplicity, we can set them on the object
        review.company_name = company_name
        review.user_name = user_name
        return review
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving review: {str(e)}")

@router.put("/{review_id}", response_model=ReviewSchema)
async def update_review(review_id: str, review_update: ReviewUpdate, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(ReviewModel).where(ReviewModel.id == review_id)
        result = await db.execute(stmt)
        db_review = result.scalar_one_or_none()
        if not db_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        update_data = review_update.model_dump(exclude_unset=True)
        
        # Validate ratings if they are being updated
        rating_fields = ['rating_work_culture', 'rating_salary', 'rating_hr', 'rating_management']
        for field in rating_fields:
            if field in update_data and update_data[field] is not None:
                if not 1 <= update_data[field] <= 5:
                    raise HTTPException(status_code=400, detail=f"{field.replace('rating_', '').replace('_', ' ').capitalize()} rating must be between 1 and 5")
        
        for key, value in update_data.items():
            setattr(db_review, key, value)
            
        db_review.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(db_review)
        return db_review
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating review: {str(e)}")

@router.delete("/{review_id}")
async def delete_review(review_id: str, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(ReviewModel).where(ReviewModel.id == review_id)
        result = await db.execute(stmt)
        db_review = result.scalar_one_or_none()
        if not db_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        await db.delete(db_review)
        await db.commit()
        return {"message": "Review deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting review: {str(e)}")

@router.get("/", response_model=List[ReviewSchema])
async def list_reviews(
    company_id: str = Query(None, description="Filter by company ID"),
    user_id: str = Query(None, description="Filter by user ID"),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(ReviewModel, CompanyModel.name.label("company_name"), UserModel.full_name.label("user_name"))\
            .join(CompanyModel, ReviewModel.company_id == CompanyModel.id)\
            .join(UserModel, ReviewModel.user_id == UserModel.id)
            
        if company_id:
            stmt = stmt.where(ReviewModel.company_id == company_id)
        if user_id:
            stmt = stmt.where(ReviewModel.user_id == user_id)
            
        stmt = stmt.order_by(ReviewModel.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        reviews = []
        for review, company_name, user_name in result.all():
            review.company_name = company_name
            review.user_name = user_name
            reviews.append(review)
            
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing reviews: {str(e)}")

@router.get("/company/{company_id}/average")
async def get_company_average_ratings(company_id: str, db: AsyncSession = Depends(get_db)):
    """Get average ratings for a company"""
    try:
        # Check if company exists
        comp_stmt = select(CompanyModel).where(CompanyModel.id == company_id)
        comp_result = await db.execute(comp_stmt)
        company = comp_result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Calculate average ratings
        stmt = select(
            func.avg(ReviewModel.rating_work_culture).label("avg_work_culture"),
            func.avg(ReviewModel.rating_salary).label("avg_salary"),
            func.avg(ReviewModel.rating_hr).label("avg_hr"),
            func.avg(ReviewModel.rating_management).label("avg_management"),
            func.count(ReviewModel.id).label("total_reviews")
        ).where(ReviewModel.company_id == company_id)
        
        result = await db.execute(stmt)
        avg_data = result.first()
        
        if avg_data and avg_data.total_reviews > 0:
            return {
                "company_id": company_id,
                "company_name": company.name,
                "average_ratings": {
                    "work_culture": round(float(avg_data.avg_work_culture), 2),
                    "salary": round(float(avg_data.avg_salary), 2),
                    "hr": round(float(avg_data.avg_hr), 2),
                    "management": round(float(avg_data.avg_management), 2),
                },
                "total_reviews": avg_data.total_reviews
            }
        else:
            return {
                "company_id": company_id,
                "company_name": company.name,
                "average_ratings": {
                    "work_culture": 0,
                    "salary": 0,
                    "hr": 0,
                    "management": 0,
                },
                "total_reviews": 0
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating average ratings: {str(e)}")
