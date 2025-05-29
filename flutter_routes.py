# health_routes.py
from fastapi import APIRouter, HTTPException, status
import bcrypt
import uuid
from typing import List
import psycopg2

from flutter_models import (
    HealthUserCreate, HealthUserResponse, HealthLoginRequest, 
    WaterIntakeRequest, MealRequest
)
from database import get_health_db_cursor

# Create a separate router for health endpoints
health_router = APIRouter(prefix="/api/health", tags=["mobile-health"])

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

@health_router.get("/check")
async def health_check():
    """Health check for mobile app"""
    return {"status": "ok", "message": "Health API is running"}

@health_router.post("/users", response_model=HealthUserResponse)
async def create_health_user(user_profile: HealthUserCreate):
    """Create user profile for mobile app"""
    try:
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(user_profile.password)
        
        with get_health_db_cursor() as (conn, cursor):
            cursor.execute("""
                INSERT INTO users (
                    id, name, email, password_hash, gender, age, height, weight, activity_level,
                    bmi, bmr, tdee, primary_goal, weight_goal, target_weight,
                    sleep_hours, bedtime, wakeup_time, sleep_issues,
                    dietary_preferences, water_intake, medical_conditions, other_medical_condition,
                    preferred_workouts, workout_frequency, workout_duration, workout_location,
                    available_equipment, fitness_level, has_trainer
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                user_id, user_profile.name, user_profile.email, hashed_password,
                user_profile.gender, user_profile.age, user_profile.height, user_profile.weight,
                user_profile.activityLevel,
                user_profile.bmi or (user_profile.formData or {}).get('bmi', 0),
                user_profile.bmr or (user_profile.formData or {}).get('bmr', 0),
                user_profile.tdee or (user_profile.formData or {}).get('tdee', 0),
                user_profile.primaryGoal, user_profile.weightGoal, user_profile.targetWeight,
                user_profile.sleepHours, user_profile.bedtime, user_profile.wakeupTime,
                user_profile.sleepIssues, user_profile.dietaryPreferences, user_profile.waterIntake,
                user_profile.medicalConditions, user_profile.otherMedicalCondition,
                user_profile.preferredWorkouts, user_profile.workoutFrequency, user_profile.workoutDuration,
                user_profile.workoutLocation, user_profile.availableEquipment, user_profile.fitnessLevel,
                user_profile.hasTrainer
            ))
            conn.commit()
            
        return HealthUserResponse(success=True, userId=user_id)
        
    except psycopg2.IntegrityError as e:
        if 'users_email_key' in str(e):
            raise HTTPException(status_code=400, detail="Email already exists")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/login", response_model=HealthUserResponse)
async def login_health_user(login_data: HealthLoginRequest):
    """Login for mobile app users"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            cursor.execute(
                'SELECT id, password_hash FROM users WHERE email = %s', 
                (login_data.email,)
            )
            user = cursor.fetchone()
            
            if not user or not verify_password(login_data.password, user['password_hash']):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
        return HealthUserResponse(success=True, userId=user['id'])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/users/{user_id}", response_model=HealthUserResponse)
async def get_health_user_profile(user_id: str):
    """Get user profile for mobile app"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT * FROM users WHERE id = %s
            """, (user_id,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Format for Flutter app
            user_profile = {
                'name': user_data['name'],
                'email': user_data['email'],
                'gender': user_data['gender'],
                'age': user_data['age'],
                'height': user_data['height'],
                'weight': user_data['weight'],
                'activityLevel': user_data['activity_level'],
                'primaryGoal': user_data['primary_goal'] or '',
                'weightGoal': user_data['weight_goal'] or '',
                'targetWeight': user_data['target_weight'] or 0,
                'sleepHours': user_data['sleep_hours'] or 7,
                'bedtime': user_data['bedtime'] or '',
                'wakeupTime': user_data['wakeup_time'] or '',
                'sleepIssues': user_data['sleep_issues'] or [],
                'dietaryPreferences': user_data['dietary_preferences'] or [],
                'waterIntake': user_data['water_intake'] or 2.0,
                'medicalConditions': user_data['medical_conditions'] or [],
                'otherMedicalCondition': user_data['other_medical_condition'] or '',
                'preferredWorkouts': user_data['preferred_workouts'] or [],
                'workoutFrequency': user_data['workout_frequency'] or 3,
                'workoutDuration': user_data['workout_duration'] or 30,
                'workoutLocation': user_data['workout_location'] or '',
                'availableEquipment': user_data['available_equipment'] or [],
                'fitnessLevel': user_data['fitness_level'] or 'Beginner',
                'hasTrainer': user_data['has_trainer'] or False,
                'formData': {
                    'bmi': user_data['bmi'] or 0,
                    'bmr': user_data['bmr'] or 0,
                    'tdee': user_data['tdee'] or 0,
                }
            }
            
        return HealthUserResponse(success=True, userProfile=user_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))