# exercise_api.py
"""
Exercise logging and tracking API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
from database import SessionLocal, User
from sqlalchemy import select, text
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
    
@exercise_router.get("/history/{user_id}")
async def get_exercise_history(
    user_id: str,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20
):
    """
    Get exercise history for a user with optional date filtering
    """
    try:
        print(f"📍 Getting exercise history for user {user_id}, date: {date}")
        
        async with SessionLocal() as session:
            # First ensure the table exists
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
            
            # Build the query
            query = text("""
                SELECT * FROM exercise_logs 
                WHERE user_id = :user_id
            """)
            
            params = {"user_id": user_id}
            
            # Handle date filtering
            if date:
                # If a specific date is provided, get exercises for that day
                target_date = datetime.fromisoformat(date.replace('Z', '+00:00')).date()
                start_of_day = datetime.combine(target_date, datetime.min.time())
                end_of_day = start_of_day + timedelta(days=1)
                
                query = text("""
                    SELECT * FROM exercise_logs 
                    WHERE user_id = :user_id 
                    AND exercise_date >= :start_date 
                    AND exercise_date < :end_date
                    ORDER BY exercise_date DESC
                    LIMIT :limit
                """)
                params.update({
                    "start_date": start_of_day,
                    "end_date": end_of_day,
                    "limit": limit
                })
            elif start_date and end_date:
                # Date range filtering
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                
                query = text("""
                    SELECT * FROM exercise_logs 
                    WHERE user_id = :user_id 
                    AND exercise_date >= :start_date 
                    AND exercise_date <= :end_date
                    ORDER BY exercise_date DESC
                    LIMIT :limit
                """)
                params.update({
                    "start_date": start,
                    "end_date": end,
                    "limit": limit
                })
            else:
                # No date filter, get recent exercises
                query = text("""
                    SELECT * FROM exercise_logs 
                    WHERE user_id = :user_id 
                    ORDER BY exercise_date DESC
                    LIMIT :limit
                """)
                params["limit"] = limit
            
            result = await session.execute(query, params)
            logs = result.fetchall()
            
            # Convert to dictionary format
            exercise_logs = []
            for log in logs:
                exercise_logs.append({
                    "id": str(log.id),
                    "exercise_name": log.exercise_name,
                    "exercise_type": log.exercise_type,
                    "duration_minutes": log.duration_minutes,
                    "calories_burned": float(log.calories_burned) if log.calories_burned else 0,
                    "distance_km": float(log.distance_km) if log.distance_km else None,
                    "sets": log.sets,
                    "reps": log.reps,
                    "weight_kg": float(log.weight_kg) if log.weight_kg else None,
                    "intensity": log.intensity,
                    "notes": log.notes,
                    "exercise_date": log.exercise_date.isoformat() if log.exercise_date else None,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                })
            
            print(f"✅ Found {len(exercise_logs)} exercises")
            
            return {
                "success": True,
                "exercises": exercise_logs,
                "count": len(exercise_logs)
            }
            
    except Exception as e:
        print(f"❌ Error fetching exercise history: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@exercise_router.delete("/{exercise_id}")
async def delete_exercise(exercise_id: str):
    """
    Delete an exercise log entry
    """
    try:
        async with SessionLocal() as session:
            result = await session.execute(
                text("DELETE FROM exercise_logs WHERE id = :id"),
                {"id": exercise_id}
            )
            await session.commit()
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Exercise not found")
            
            return {"success": True, "message": "Exercise deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting exercise: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@exercise_router.put("/{exercise_id}")
async def update_exercise(exercise_id: str, request: ExerciseUpdateRequest):
    """
    Update an existing exercise log entry
    """
    try:
        async with SessionLocal() as session:
            # Build dynamic update query based on provided fields
            update_fields = []
            params = {"id": exercise_id}
            
            if request.duration_minutes is not None:
                update_fields.append("duration_minutes = :duration_minutes")
                params["duration_minutes"] = request.duration_minutes
            
            if request.calories_burned is not None:
                update_fields.append("calories_burned = :calories_burned")
                params["calories_burned"] = request.calories_burned
            
            if request.distance_km is not None:
                update_fields.append("distance_km = :distance_km")
                params["distance_km"] = request.distance_km
            
            if request.intensity is not None:
                update_fields.append("intensity = :intensity")
                params["intensity"] = request.intensity
            
            if request.notes is not None:
                update_fields.append("notes = :notes")
                params["notes"] = request.notes
            
            if request.sets is not None:
                update_fields.append("sets = :sets")
                params["sets"] = request.sets
            
            if request.reps is not None:
                update_fields.append("reps = :reps")
                params["reps"] = request.reps
            
            if request.weight_kg is not None:
                update_fields.append("weight_kg = :weight_kg")
                params["weight_kg"] = request.weight_kg
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            query = text(f"""
                UPDATE exercise_logs 
                SET {', '.join(update_fields)}
                WHERE id = :id
                RETURNING *
            """)
            
            result = await session.execute(query, params)
            updated_exercise = result.fetchone()
            await session.commit()
            
            if not updated_exercise:
                raise HTTPException(status_code=404, detail="Exercise not found")
            
            return {
                "success": True,
                "message": "Exercise updated successfully",
                "exercise": {
                    "id": str(updated_exercise.id),
                    "exercise_name": updated_exercise.exercise_name,
                    "duration_minutes": updated_exercise.duration_minutes,
                    "calories_burned": float(updated_exercise.calories_burned) if updated_exercise.calories_burned else None,
                    "intensity": updated_exercise.intensity
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating exercise: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@exercise_router.get("/weekly-summary/{user_id}")
async def get_weekly_summary(user_id: str):
    """
    Get weekly exercise summary for the user
    """
    try:
        async with SessionLocal() as session:
            # Get exercises from the last 7 days
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_workouts,
                    SUM(duration_minutes) as total_minutes,
                    SUM(calories_burned) as total_calories,
                    AVG(duration_minutes) as avg_duration,
                    DATE(exercise_date) as workout_date
                FROM exercise_logs
                WHERE user_id = :user_id 
                AND exercise_date >= :start_date
                GROUP BY DATE(exercise_date)
                ORDER BY workout_date DESC
            """), {
                "user_id": user_id,
                "start_date": seven_days_ago
            })
            
            daily_summaries = result.fetchall()
            
            # Get exercise type distribution
            type_result = await session.execute(text("""
                SELECT 
                    exercise_type,
                    COUNT(*) as count,
                    SUM(duration_minutes) as total_minutes
                FROM exercise_logs
                WHERE user_id = :user_id 
                AND exercise_date >= :start_date
                GROUP BY exercise_type
            """), {
                "user_id": user_id,
                "start_date": seven_days_ago
            })
            
            type_distribution = type_result.fetchall()
            
            # Calculate totals
            total_workouts = sum(day.total_workouts for day in daily_summaries)
            total_minutes = sum(day.total_minutes or 0 for day in daily_summaries)
            total_calories = sum(day.total_calories or 0 for day in daily_summaries)
            
            return {
                "success": True,
                "summary": {
                    "total_workouts": total_workouts,
                    "total_minutes": total_minutes,
                    "total_calories": float(total_calories) if total_calories else 0,
                    "average_duration": float(total_minutes / total_workouts) if total_workouts > 0 else 0,
                    "daily_breakdown": [
                        {
                            "date": day.workout_date.isoformat(),
                            "workouts": day.total_workouts,
                            "minutes": day.total_minutes,
                            "calories": float(day.total_calories) if day.total_calories else 0
                        }
                        for day in daily_summaries
                    ],
                    "exercise_types": [
                        {
                            "type": type_data.exercise_type,
                            "count": type_data.count,
                            "total_minutes": type_data.total_minutes
                        }
                        for type_data in type_distribution
                    ]
                }
            }
            
    except Exception as e:
        print(f"❌ Error getting weekly summary: {e}")
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