from fastapi import APIRouter, HTTPException, status, Query
from app.models.review import ReviewCreate, ReviewUpdate, Review
from app.database.database import reviews_collection, companies_collection, users_collection
from bson import ObjectId
from datetime import datetime
from typing import List

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])

@router.post("/", response_model=Review)
async def create_review(review: ReviewCreate):
    try:
        # Check if company exists
        company = await companies_collection.find_one({"_id": ObjectId(review.company_id)})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Check if user exists
        user = await users_collection.find_one({"_id": ObjectId(review.user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has already reviewed this company
        existing_review = await reviews_collection.find_one({
            "company_id": review.company_id,
            "user_id": review.user_id
        })
        if existing_review:
            raise HTTPException(status_code=400, detail="You have already reviewed this company")
        
        # Validate ratings are between 1-5
        if not 1 <= review.rating_work_culture <= 5:
            raise HTTPException(status_code=400, detail="Work culture rating must be between 1 and 5")
        if not 1 <= review.rating_salary <= 5:
            raise HTTPException(status_code=400, detail="Salary rating must be between 1 and 5")
        if not 1 <= review.rating_hr <= 5:
            raise HTTPException(status_code=400, detail="HR rating must be between 1 and 5")
        if not 1 <= review.rating_management <= 5:
            raise HTTPException(status_code=400, detail="Management rating must be between 1 and 5")
        
        # Convert to dict and add required fields
        review_dict = review.dict()
        review_dict["created_at"] = datetime.now()
        review_dict["updated_at"] = datetime.now()
        
        result = await reviews_collection.insert_one(review_dict)
        review_dict["id"] = str(result.inserted_id)
        del review_dict["_id"]
        
        return Review(**review_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating review: {str(e)}")

@router.get("/{review_id}", response_model=Review)
async def get_review(review_id: str):
    try:
        review = await reviews_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        review["id"] = str(review["_id"])
        del review["_id"]
        
        # Get company details
        company = await companies_collection.find_one({"_id": ObjectId(review["company_id"])})
        if company:
            review["company_name"] = company.get("name", "Unknown Company")
        
        # Get user details (only public info)
        user = await users_collection.find_one({"_id": ObjectId(review["user_id"])})
        if user:
            review["user_name"] = user.get("full_name", "Anonymous User")
        
        return Review(**review)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving review: {str(e)}")

@router.put("/{review_id}", response_model=Review)
async def update_review(review_id: str, review_update: ReviewUpdate):
    try:
        existing_review = await reviews_collection.find_one({"_id": ObjectId(review_id)})
        if not existing_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Get the update data as a dict
        update_data = review_update.dict(exclude_unset=True)
        
        # Validate ratings if they are being updated
        if 'rating_work_culture' in update_data and update_data['rating_work_culture'] is not None:
            if not 1 <= update_data['rating_work_culture'] <= 5:
                raise HTTPException(status_code=400, detail="Work culture rating must be between 1 and 5")
        if 'rating_salary' in update_data and update_data['rating_salary'] is not None:
            if not 1 <= update_data['rating_salary'] <= 5:
                raise HTTPException(status_code=400, detail="Salary rating must be between 1 and 5")
        if 'rating_hr' in update_data and update_data['rating_hr'] is not None:
            if not 1 <= update_data['rating_hr'] <= 5:
                raise HTTPException(status_code=400, detail="HR rating must be between 1 and 5")
        if 'rating_management' in update_data and update_data['rating_management'] is not None:
            if not 1 <= update_data['rating_management'] <= 5:
                raise HTTPException(status_code=400, detail="Management rating must be between 1 and 5")
        
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.now()
        
        # Update the document
        result = await reviews_collection.update_one(
            {"_id": ObjectId(review_id)}, 
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Review not found or no changes made")
        
        # Fetch the updated document
        updated_review = await reviews_collection.find_one({"_id": ObjectId(review_id)})
        if updated_review:
            updated_review["id"] = str(updated_review["_id"])
            del updated_review["_id"]
            
            # Get company details
            company = await companies_collection.find_one({"_id": ObjectId(updated_review["company_id"])})
            if company:
                updated_review["company_name"] = company.get("name", "Unknown Company")
            
            # Get user details
            user = await users_collection.find_one({"_id": ObjectId(updated_review["user_id"])})
            if user:
                updated_review["user_name"] = user.get("full_name", "Anonymous User")
            
            # Create a complete review object to return
            review_data = {
                "company_id": updated_review.get("company_id", existing_review["company_id"]),
                "user_id": updated_review.get("user_id", existing_review["user_id"]),
                "rating_work_culture": updated_review.get("rating_work_culture", existing_review["rating_work_culture"]),
                "rating_salary": updated_review.get("rating_salary", existing_review["rating_salary"]),
                "rating_hr": updated_review.get("rating_hr", existing_review["rating_hr"]),
                "rating_management": updated_review.get("rating_management", existing_review["rating_management"]),
                "pros": updated_review.get("pros", existing_review["pros"]),
                "cons": updated_review.get("cons", existing_review["cons"]),
                "interview_experience": updated_review.get("interview_experience", existing_review.get("interview_experience")),
                "id": updated_review["id"],
                "created_at": updated_review.get("created_at", existing_review["created_at"]),
                "updated_at": updated_review.get("updated_at", datetime.now())
            }
            
            return Review(**review_data)
        else:
            raise HTTPException(status_code=404, detail="Review not found after update")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating review: {str(e)}")

@router.delete("/{review_id}")
async def delete_review(review_id: str):
    try:
        review = await reviews_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        await reviews_collection.delete_one({"_id": ObjectId(review_id)})
        return {"message": "Review deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting review: {str(e)}")

@router.get("/", response_model=List[Review])
async def list_reviews(
    company_id: str = Query(None, description="Filter by company ID"),
    user_id: str = Query(None, description="Filter by user ID"),
    skip: int = 0,
    limit: int = 20
):
    try:
        query = {}
        if company_id:
            query["company_id"] = company_id
        if user_id:
            query["user_id"] = user_id
        
        reviews = []
        cursor = reviews_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        async for review in cursor:
            review_obj = {
                "company_id": review.get("company_id", ""),
                "user_id": review.get("user_id", ""),
                "rating_work_culture": review.get("rating_work_culture", 0),
                "rating_salary": review.get("rating_salary", 0),
                "rating_hr": review.get("rating_hr", 0),
                "rating_management": review.get("rating_management", 0),
                "pros": review.get("pros", ""),
                "cons": review.get("cons", ""),
                "interview_experience": review.get("interview_experience", ""),
                "id": str(review["_id"]),
                "created_at": review.get("created_at", datetime.now()),
                "updated_at": review.get("updated_at", datetime.now())
            }
            del review["_id"]
            
            # Get company details
            company = await companies_collection.find_one({"_id": ObjectId(review_obj["company_id"])})
            if company:
                review_obj["company_name"] = company.get("name", "Unknown Company")
            
            # Get user details
            user = await users_collection.find_one({"_id": ObjectId(review_obj["user_id"])})
            if user:
                review_obj["user_name"] = user.get("full_name", "Anonymous User")
            
            reviews.append(Review(**review_obj))
        
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing reviews: {str(e)}")

@router.get("/company/{company_id}/average")
async def get_company_average_ratings(company_id: str):
    """Get average ratings for a company"""
    try:
        # Check if company exists
        company = await companies_collection.find_one({"_id": ObjectId(company_id)})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Calculate average ratings
        pipeline = [
            {"$match": {"company_id": company_id}},
            {
                "$group": {
                    "_id": None,
                    "avg_work_culture": {"$avg": "$rating_work_culture"},
                    "avg_salary": {"$avg": "$rating_salary"},
                    "avg_hr": {"$avg": "$rating_hr"},
                    "avg_management": {"$avg": "$rating_management"},
                    "total_reviews": {"$sum": 1}
                }
            }
        ]
        
        result = await reviews_collection.aggregate(pipeline).to_list(length=1)
        
        if result:
            avg_data = result[0]
            return {
                "company_id": company_id,
                "company_name": company.get("name", "Unknown Company"),
                "average_ratings": {
                    "work_culture": round(avg_data["avg_work_culture"], 2),
                    "salary": round(avg_data["avg_salary"], 2),
                    "hr": round(avg_data["avg_hr"], 2),
                    "management": round(avg_data["avg_management"], 2),
                },
                "total_reviews": avg_data["total_reviews"]
            }
        else:
            return {
                "company_id": company_id,
                "company_name": company.get("name", "Unknown Company"),
                "average_ratings": {
                    "work_culture": 0,
                    "salary": 0,
                    "hr": 0,
                    "management": 0,
                },
                "total_reviews": 0
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating average ratings: {str(e)}")
