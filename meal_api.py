# meal_api.py
"""
Meal logging and nutrition analysis API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, timedelta
import json
import os
from openai import OpenAI
from database import SessionLocal, MealEntry, DailyNutrition, get_user_by_id
from sqlalchemy import select, and_, text
import uuid
import traceback

# Initialize router
meal_router = APIRouter(prefix="/api/health/meals", tags=["meals"])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pydantic models
class MealAnalysisRequest(BaseModel):
    user_id: str
    food_item: str
    quantity: str
    preparation: Optional[str] = ""
    meal_type: Optional[str] = "snack"
    meal_date: Optional[str] = None

class MealUpdateRequest(BaseModel):
    food_item: Optional[str] = None
    quantity: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None

@meal_router.post("/analyze")
async def analyze_meal(request: MealAnalysisRequest):
    """
    Analyze meal using AI and return nutrition information
    """
    try:
        print(f"📍 Analyzing meal for user {request.user_id}: {request.food_item}")
        
        # Get user profile for context
        user = await get_user_by_id(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create the AI prompt
        prompt = f"""
        Analyze this meal and provide accurate nutrition information.
        
        Food: {request.food_item}
        Quantity: {request.quantity}
        Preparation: {request.preparation if request.preparation else 'not specified'}
        
        User context (use for personalized suggestions):
        - Current weight: {user.weight if user.weight else 70} kg
        - Goal: {user.weight_goal or 'maintain weight'}
        - Activity level: {user.activity_level or 'moderate'}
        - TDEE: {user.tdee if user.tdee else 2000} calories
        
        Provide a JSON response with these exact fields:
        {{
            "calories": number (integer),
            "protein_g": number (to 1 decimal),
            "carbs_g": number (to 1 decimal),
            "fat_g": number (to 1 decimal),
            "fiber_g": number (to 1 decimal),
            "sugar_g": number (to 1 decimal),
            "sodium_mg": number (integer),
            "serving_description": "clear description of portion size",
            "nutrition_notes": "brief nutritional assessment",
            "healthiness_score": number (1-10),
            "suggestions": "personalized suggestion to make it healthier or fit user's goals"
        }}
        
        Be accurate and realistic with the estimates. Consider cooking methods (fried adds oil, grilled reduces fat, etc).
        """
        
        print("🤖 Calling OpenAI API...")
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using the more cost-effective model
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional nutritionist. Provide accurate nutrition estimates based on standard serving sizes and preparation methods."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3  # Lower temperature for more consistent nutrition data
        )
        
        # Parse the response
        nutrition_data = json.loads(response.choices[0].message.content)
        print(f"✅ AI analysis complete: {nutrition_data['calories']} calories")
        
        # Parse meal date
        if request.meal_date:
            meal_date = datetime.fromisoformat(request.meal_date.replace('Z', '+00:00'))
        else:
            meal_date = datetime.now()
        
        # Save to database
        async with SessionLocal() as session:
            try:
                # Create meal entry
                meal_entry = MealEntry(
                    user_id=uuid.UUID(request.user_id),
                    food_item=request.food_item,
                    quantity=request.quantity,
                    preparation=request.preparation,
                    meal_type=request.meal_type,
                    calories=nutrition_data['calories'],
                    protein_g=nutrition_data['protein_g'],
                    carbs_g=nutrition_data['carbs_g'],
                    fat_g=nutrition_data['fat_g'],
                    fiber_g=nutrition_data.get('fiber_g', 0),
                    sugar_g=nutrition_data.get('sugar_g', 0),
                    sodium_mg=nutrition_data.get('sodium_mg', 0),
                    nutrition_data=nutrition_data,
                    data_source='ai',
                    confidence_score=0.85,
                    meal_date=meal_date
                )
                
                session.add(meal_entry)
                await session.commit()
                await session.refresh(meal_entry)
                
                print(f"✅ Meal saved to database with ID: {meal_entry.id}")
                
                # Update daily nutrition totals
                await update_daily_nutrition(session, request.user_id, meal_date.date(), nutrition_data)
                
                return {
                    'success': True,
                    'meal_id': str(meal_entry.id),
                    'nutrition': nutrition_data,
                    'data_source': 'AI Analysis'
                }
                
            except Exception as db_error:
                await session.rollback()
                print(f"❌ Database error: {db_error}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error analyzing meal: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def update_daily_nutrition(session, user_id: str, date_obj: date, nutrition_data: dict):
    """Update or create daily nutrition totals"""
    try:
        print(f"📊 Updating daily nutrition for user {user_id} on {date_obj}")
        
        # Convert date to datetime for database query
        start_of_day = datetime.combine(date_obj, datetime.min.time())
        
        # Check if daily nutrition entry exists
        result = await session.execute(
            select(DailyNutrition).where(
                and_(
                    DailyNutrition.user_id == uuid.UUID(user_id),
                    DailyNutrition.date >= start_of_day,
                    DailyNutrition.date < start_of_day + timedelta(days=1)
                )
            )
        )
        daily_nutrition = result.scalars().first()
        
        if daily_nutrition:
            # Update existing entry
            print(f"📝 Updating existing daily nutrition entry")
            daily_nutrition.calories_consumed += nutrition_data['calories']
            daily_nutrition.protein_g += nutrition_data['protein_g']
            daily_nutrition.carbs_g += nutrition_data['carbs_g']
            daily_nutrition.fat_g += nutrition_data['fat_g']
            daily_nutrition.meals_logged += 1
        else:
            # Create new entry
            print(f"➕ Creating new daily nutrition entry")
            daily_nutrition = DailyNutrition(
                user_id=uuid.UUID(user_id),
                date=start_of_day,  # Use start of day as the date
                calories_consumed=nutrition_data['calories'],
                protein_g=nutrition_data['protein_g'],
                carbs_g=nutrition_data['carbs_g'],
                fat_g=nutrition_data['fat_g'],
                water_liters=0.0,
                meals_logged=1
            )
            session.add(daily_nutrition)
        
        await session.commit()
        print(f"✅ Daily nutrition updated: {daily_nutrition.calories_consumed} cal, {daily_nutrition.meals_logged} meals")
        
    except Exception as e:
        print(f"❌ Error updating daily nutrition: {e}")
        import traceback
        traceback.print_exc()

@meal_router.get("/history/{user_id}")
async def get_meal_history(
    user_id: str,
    date: Optional[str] = None,
    limit: int = 20
):
    """
    Get meal history for a user
    """
    try:
        print(f"📍 Getting meal history for user {user_id}, date: {date}")
        
        async with SessionLocal() as session:
            query = select(MealEntry).where(
                MealEntry.user_id == uuid.UUID(user_id)
            )
            
            # Filter by date if provided
            if date:
                target_date = datetime.fromisoformat(date.replace('Z', '+00:00')).date()
                start_of_day = datetime.combine(target_date, datetime.min.time())
                end_of_day = start_of_day + timedelta(days=1)
                
                query = query.where(
                    and_(
                        MealEntry.meal_date >= start_of_day,
                        MealEntry.meal_date < end_of_day
                    )
                )
            
            query = query.order_by(MealEntry.meal_date.desc()).limit(limit)
            
            result = await session.execute(query)
            meals = result.scalars().all()
            
            print(f"✅ Found {len(meals)} meals")
            
            return {
                'success': True,
                'meals': [
                    {
                        'id': str(meal.id),
                        'food_item': meal.food_item,
                        'quantity': meal.quantity,
                        'preparation': meal.preparation,
                        'meal_type': meal.meal_type,
                        'calories': meal.calories,
                        'protein_g': meal.protein_g,
                        'carbs_g': meal.carbs_g,
                        'fat_g': meal.fat_g,
                        'fiber_g': meal.fiber_g,
                        'sugar_g': meal.sugar_g,
                        'sodium_mg': meal.sodium_mg,
                        'meal_date': meal.meal_date.isoformat(),
                        'data_source': meal.data_source
                    }
                    for meal in meals
                ]
            }
            
    except Exception as e:
        print(f"❌ Error fetching meal history: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@meal_router.put("/{meal_id}")
async def update_meal(meal_id: str, update_data: MealUpdateRequest):
    """
    Update an existing meal entry
    """
    try:
        print(f"📍 Updating meal {meal_id}")
        
        async with SessionLocal() as session:
            # Get the meal
            result = await session.execute(
                select(MealEntry).where(MealEntry.id == uuid.UUID(meal_id))
            )
            meal = result.scalars().first()
            
            if not meal:
                raise HTTPException(status_code=404, detail="Meal not found")
            
            # Store old values for daily nutrition update
            old_nutrition = {
                'calories': meal.calories,
                'protein_g': meal.protein_g,
                'carbs_g': meal.carbs_g,
                'fat_g': meal.fat_g
            }
            
            # Update fields if provided
            if update_data.food_item is not None:
                meal.food_item = update_data.food_item
            if update_data.quantity is not None:
                meal.quantity = update_data.quantity
            if update_data.calories is not None:
                meal.calories = update_data.calories
            if update_data.protein_g is not None:
                meal.protein_g = update_data.protein_g
            if update_data.carbs_g is not None:
                meal.carbs_g = update_data.carbs_g
            if update_data.fat_g is not None:
                meal.fat_g = update_data.fat_g
                
            meal.updated_at = datetime.now()
            
            await session.commit()
            await session.refresh(meal)
            
            # Update daily nutrition totals
            # Subtract old values and add new values
            result = await session.execute(
                select(DailyNutrition).where(
                    and_(
                        DailyNutrition.user_id == meal.user_id,
                        DailyNutrition.date == meal.meal_date.date()
                    )
                )
            )
            daily_nutrition = result.scalars().first()
            
            if daily_nutrition:
                daily_nutrition.calories_consumed -= old_nutrition['calories']
                daily_nutrition.calories_consumed += meal.calories
                daily_nutrition.protein_g -= old_nutrition['protein_g']
                daily_nutrition.protein_g += meal.protein_g
                daily_nutrition.carbs_g -= old_nutrition['carbs_g']
                daily_nutrition.carbs_g += meal.carbs_g
                daily_nutrition.fat_g -= old_nutrition['fat_g']
                daily_nutrition.fat_g += meal.fat_g
                
                await session.commit()
            
            print(f"✅ Meal updated successfully")
            
            return {
                'success': True,
                'message': 'Meal updated successfully',
                'meal': {
                    'id': str(meal.id),
                    'food_item': meal.food_item,
                    'quantity': meal.quantity,
                    'calories': meal.calories,
                    'protein_g': meal.protein_g,
                    'carbs_g': meal.carbs_g,
                    'fat_g': meal.fat_g
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating meal: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@meal_router.delete("/{meal_id}")
async def delete_meal(meal_id: str):
    """
    Delete a meal entry
    """
    try:
        print(f"📍 Deleting meal {meal_id}")
        
        async with SessionLocal() as session:
            result = await session.execute(
                select(MealEntry).where(MealEntry.id == uuid.UUID(meal_id))
            )
            meal = result.scalars().first()
            
            if not meal:
                raise HTTPException(status_code=404, detail="Meal not found")
            
            # Store nutrition data for daily totals update
            user_id = meal.user_id
            meal_date = meal.meal_date.date()
            nutrition_to_subtract = {
                'calories': meal.calories,
                'protein_g': meal.protein_g,
                'carbs_g': meal.carbs_g,
                'fat_g': meal.fat_g
            }
            
            # Delete the meal
            await session.delete(meal)
            await session.commit()
            
            # Update daily nutrition totals
            result = await session.execute(
                select(DailyNutrition).where(
                    and_(
                        DailyNutrition.user_id == user_id,
                        DailyNutrition.date == meal_date
                    )
                )
            )
            daily_nutrition = result.scalars().first()
            
            if daily_nutrition:
                daily_nutrition.calories_consumed -= nutrition_to_subtract['calories']
                daily_nutrition.protein_g -= nutrition_to_subtract['protein_g']
                daily_nutrition.carbs_g -= nutrition_to_subtract['carbs_g']
                daily_nutrition.fat_g -= nutrition_to_subtract['fat_g']
                daily_nutrition.meals_logged -= 1
                
                await session.commit()
            
            print(f"✅ Meal deleted successfully")
            
            return {'success': True, 'message': 'Meal deleted successfully'}
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting meal: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@meal_router.get("/daily-summary/{user_id}")
async def get_daily_summary(
    user_id: str,
    date: Optional[str] = None
):
    """
    Get daily nutrition summary including meal counts and exercise data
    """
    try:
        # Use provided date or today
        if date:
            target_date = datetime.fromisoformat(date.replace('Z', '+00:00')).date()
        else:
            target_date = datetime.now().date()
        
        print(f"📊 Getting daily summary for user {user_id} on {target_date}")
        
        async with SessionLocal() as session:
            # Get meal data for the day
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)
            
            # Count meals by type
            meal_result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_meals,
                    SUM(calories) as total_calories,
                    SUM(protein_g) as total_protein,
                    SUM(carbs_g) as total_carbs,
                    SUM(fat_g) as total_fat,
                    COUNT(CASE WHEN meal_type = 'breakfast' THEN 1 END) as breakfast_count,
                    COUNT(CASE WHEN meal_type = 'lunch' THEN 1 END) as lunch_count,
                    COUNT(CASE WHEN meal_type = 'dinner' THEN 1 END) as dinner_count,
                    COUNT(CASE WHEN meal_type = 'snack' THEN 1 END) as snack_count
                FROM meal_entries
                WHERE user_id = :user_id 
                AND meal_date >= :start_date 
                AND meal_date < :end_date
            """), {
                "user_id": user_id,
                "start_date": start_of_day,
                "end_date": end_of_day
            })
            
            meal_data = meal_result.fetchone()
            
            # Get exercise data for the day
            exercise_result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_exercises,
                    SUM(duration_minutes) as total_minutes,
                    SUM(calories_burned) as calories_burned
                FROM exercise_logs
                WHERE user_id = :user_id 
                AND exercise_date >= :start_date 
                AND exercise_date < :end_date
            """), {
                "user_id": user_id,
                "start_date": start_of_day,
                "end_date": end_of_day
            })
            
            exercise_data = exercise_result.fetchone()
            
            # Build response
            return {
                "success": True,
                "date": target_date.isoformat(),
                "meals": {
                    "total_count": meal_data.total_meals or 0,
                    "breakfast": meal_data.breakfast_count or 0,
                    "lunch": meal_data.lunch_count or 0,
                    "dinner": meal_data.dinner_count or 0,
                    "snacks": meal_data.snack_count or 0,
                    "calories_consumed": float(meal_data.total_calories or 0),
                    "protein_g": float(meal_data.total_protein or 0),
                    "carbs_g": float(meal_data.total_carbs or 0),
                    "fat_g": float(meal_data.total_fat or 0)
                },
                "exercise": {
                    "total_count": exercise_data.total_exercises or 0,
                    "total_minutes": exercise_data.total_minutes or 0,
                    "calories_burned": float(exercise_data.calories_burned or 0)
                }
            }
            
    except Exception as e:
        print(f"❌ Error getting daily summary: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "meals": {"total_count": 0},
            "exercise": {"total_count": 0, "total_minutes": 0}
        }