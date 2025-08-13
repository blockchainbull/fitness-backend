# exercise_api.py
"""
Exercise logging and tracking API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from database import SessionLocal, User
from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import traceback

# Initialize router
exercise_router = APIRouter(prefix="/api/health/exercise", tags=["exercise"])

# Pydantic models
class ExerciseLogRequest(BaseModel):
    user_id: str
    exercise_name: str
    exercise_type: str  # cardio, strength, flexibility, sports, etc.
    duration_minutes: int
    calories_burned: Optional[float] = None
    distance_km: Optional[float] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    intensity: Optional[str] = "moderate"  # low, moderate, high
    notes: Optional[str] = None
    exercise_date: Optional[str] = None

class ExerciseUpdateRequest(BaseModel):
    duration_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    distance_km: Optional[float] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    intensity: Optional[str] = None
    notes: Optional[str] = None

class ExerciseStatsResponse(BaseModel):
    total_workouts: int
    total_duration_minutes: int
    total_calories_burned: float
    average_duration: float
    favorite_exercise_type: str
    current_streak: int
    longest_streak: int
    this_week_workouts: int
    this_month_workouts: int

@exercise_router.post("/log")
async def log_exercise(request: ExerciseLogRequest):
    """
    Log a new exercise session
    """
    try:
        print(f"📝 Logging exercise for user {request.user_id}: {request.exercise_name}")
        
        async with SessionLocal() as session:
            # Verify user exists
            user_result = await session.execute(
                select(User).where(User.id == request.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Calculate calories if not provided
            if request.calories_burned is None:
                # Basic calorie calculation based on activity and user weight
                weight_kg = user.weight or 70
                met_values = {
                    "low": 3.0,
                    "moderate": 5.0,
                    "high": 8.0
                }
                met = met_values.get(request.intensity, 5.0)
                request.calories_burned = (met * weight_kg * request.duration_minutes) / 60
            
            # Parse exercise date
            if request.exercise_date:
                exercise_date = datetime.fromisoformat(request.exercise_date.replace('Z', '+00:00'))
            else:
                exercise_date = datetime.now()
            
            # Create exercise log entry
            exercise_id = str(uuid.uuid4())
            
            await session.execute(text("""
                INSERT INTO exercise_logs (
                    id, user_id, exercise_name, exercise_type, 
                    duration_minutes, calories_burned, distance_km,
                    sets, reps, weight_kg, intensity, notes, exercise_date
                ) VALUES (
                    :id, :user_id, :exercise_name, :exercise_type,
                    :duration_minutes, :calories_burned, :distance_km,
                    :sets, :reps, :weight_kg, :intensity, :notes, :exercise_date
                )
            """), {
                "id": exercise_id,
                "user_id": request.user_id,
                "exercise_name": request.exercise_name,
                "exercise_type": request.exercise_type,
                "duration_minutes": request.duration_minutes,
                "calories_burned": request.calories_burned,
                "distance_km": request.distance_km,
                "sets": request.sets,
                "reps": request.reps,
                "weight_kg": request.weight_kg,
                "intensity": request.intensity,
                "notes": request.notes,
                "exercise_date": exercise_date
            })
            
            await session.commit()
            
            return {
                "success": True,
                "exercise_id": exercise_id,
                "message": "Exercise logged successfully",
                "calories_burned": request.calories_burned
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error logging exercise: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@exercise_router.get("/logs/{user_id}")
async def get_exercise_logs(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    exercise_type: Optional[str] = None,
    limit: int = 50
):
    """
    Get exercise logs for a user with optional filters
    """
    try:
        async with SessionLocal() as session:
            # First, verify the exercise_logs table exists
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS exercise_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    exercise_name VARCHAR(100) NOT NULL,
                    exercise_type VARCHAR(50) NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    calories_burned FLOAT,
                    distance_km FLOAT,
                    sets INTEGER,
                    reps INTEGER,
                    weight_kg FLOAT,
                    intensity VARCHAR(20) DEFAULT 'moderate',
                    notes VARCHAR(500),
                    exercise_date TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await session.commit()
            
            # Build the query with parameters
            query_parts = ["SELECT * FROM exercise_logs WHERE user_id = :user_id"]
            params = {"user_id": user_id}
            
            if start_date:
                query_parts.append("AND exercise_date >= :start_date")
                params["start_date"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            if end_date:
                query_parts.append("AND exercise_date <= :end_date")
                params["end_date"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            if exercise_type:
                query_parts.append("AND exercise_type = :exercise_type")
                params["exercise_type"] = exercise_type
            
            query_parts.append("ORDER BY exercise_date DESC")
            query_parts.append("LIMIT :limit")
            params["limit"] = limit
            
            query = text(" ".join(query_parts))
            result = await session.execute(query, params)
            logs = result.fetchall()
            
            # Convert Row objects to dictionaries properly
            exercise_logs = []
            for log in logs:
                # Access row data by column name
                log_dict = {
                    "id": str(log.id) if log.id else None,
                    "exercise_name": log.exercise_name,
                    "exercise_type": log.exercise_type,
                    "duration_minutes": log.duration_minutes,
                    "calories_burned": float(log.calories_burned) if log.calories_burned else None,
                    "distance_km": float(log.distance_km) if log.distance_km else None,
                    "sets": log.sets,
                    "reps": log.reps,
                    "weight_kg": float(log.weight_kg) if log.weight_kg else None,
                    "intensity": log.intensity,
                    "notes": log.notes,
                    "exercise_date": log.exercise_date.isoformat() if log.exercise_date else None,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                exercise_logs.append(log_dict)
            
            return {
                "success": True,
                "logs": exercise_logs,
                "count": len(exercise_logs)
            }
            
    except Exception as e:
        print(f"❌ Error fetching exercise logs: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@exercise_router.get("/stats/{user_id}")
async def get_exercise_stats(user_id: str):
    """
    Get exercise statistics for a user
    """
    try:
        async with SessionLocal() as session:
            # Ensure table exists
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS exercise_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    exercise_name VARCHAR(100) NOT NULL,
                    exercise_type VARCHAR(50) NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    calories_burned FLOAT,
                    distance_km FLOAT,
                    sets INTEGER,
                    reps INTEGER,
                    weight_kg FLOAT,
                    intensity VARCHAR(20) DEFAULT 'moderate',
                    notes VARCHAR(500),
                    exercise_date TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await session.commit()
            
            # Get total stats
            stats_result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_workouts,
                    COALESCE(SUM(duration_minutes), 0) as total_duration,
                    COALESCE(SUM(calories_burned), 0) as total_calories,
                    COALESCE(AVG(duration_minutes), 0) as avg_duration
                FROM exercise_logs
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            stats = stats_result.fetchone()
            
            # Get favorite exercise type
            type_result = await session.execute(text("""
                SELECT exercise_type, COUNT(*) as count
                FROM exercise_logs
                WHERE user_id = :user_id
                GROUP BY exercise_type
                ORDER BY count DESC
                LIMIT 1
            """), {"user_id": user_id})
            
            favorite_type = type_result.fetchone()
            
            # Get this week's workouts
            week_result = await session.execute(text("""
                SELECT COUNT(*) as week_count
                FROM exercise_logs
                WHERE user_id = :user_id
                AND exercise_date >= :week_start
            """), {
                "user_id": user_id,
                "week_start": datetime.now() - timedelta(days=7)
            })
            
            week_stats = week_result.fetchone()
            
            # Get this month's workouts
            month_result = await session.execute(text("""
                SELECT COUNT(*) as month_count
                FROM exercise_logs
                WHERE user_id = :user_id
                AND exercise_date >= :month_start
            """), {
                "user_id": user_id,
                "month_start": datetime.now() - timedelta(days=30)
            })
            
            month_stats = month_result.fetchone()
            
            return {
                "success": True,
                "stats": {
                    "total_workouts": int(stats.total_workouts) if stats else 0,
                    "total_duration_minutes": int(stats.total_duration) if stats else 0,
                    "total_calories_burned": float(stats.total_calories) if stats else 0.0,
                    "average_duration": float(stats.avg_duration) if stats else 0.0,
                    "favorite_exercise_type": favorite_type.exercise_type if favorite_type else "None",
                    "current_streak": 0,  # Simplified for now
                    "longest_streak": 0,  # Simplified for now
                    "this_week_workouts": int(week_stats.week_count) if week_stats else 0,
                    "this_month_workouts": int(month_stats.month_count) if month_stats else 0
                }
            }
            
    except Exception as e:
        print(f"❌ Error fetching exercise stats: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@exercise_router.delete("/log/{exercise_id}")
async def delete_exercise_log(exercise_id: str, user_id: str):
    """
    Delete an exercise log entry
    """
    try:
        async with SessionLocal() as session:
            # Verify ownership
            result = await session.execute(text("""
                DELETE FROM exercise_logs
                WHERE id = :exercise_id AND user_id = :user_id
                RETURNING id
            """), {
                "exercise_id": exercise_id,
                "user_id": user_id
            })
            
            deleted = result.fetchone()
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Exercise log not found")
            
            await session.commit()
            
            return {
                "success": True,
                "message": "Exercise log deleted successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting exercise log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def calculate_streak(dates: List[date]) -> int:
    """Calculate current workout streak"""
    if not dates:
        return 0
    
    streak = 0
    today = date.today()
    current_date = today
    
    for workout_date in dates:
        if workout_date == current_date or workout_date == current_date - timedelta(days=1):
            streak += 1
            current_date = workout_date
        else:
            break
    
    return streak