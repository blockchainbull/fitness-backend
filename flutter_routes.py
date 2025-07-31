# flutter_routes.py - Updated to use unified backend
from fastapi import APIRouter, HTTPException
import traceback

from flutter_models import (
    HealthUserCreate, HealthUserResponse, HealthLoginRequest, 
    WaterIntakeRequest, MealRequest, UnifiedOnboardingRequest
)
from database import create_user_from_onboarding, get_user_by_email, verify_password, get_user_profile

# Create a separate router for health endpoints
health_router = APIRouter(prefix="/api/health", tags=["mobile-health"])

@health_router.get("/check")
async def health_check():
    """Health check for mobile app"""
    return {"status": "ok", "message": "Health API is running"}

@health_router.post("/users", response_model=HealthUserResponse)
async def create_health_user(user_profile: HealthUserCreate):
    """Create user profile for mobile app using unified backend"""
    try:
        # Convert Flutter model to onboarding format
        onboarding_data = {
            "basicInfo": {
                "name": user_profile.name,
                "email": user_profile.email,
                "password": user_profile.password,
                "gender": user_profile.gender,
                "age": user_profile.age,
                "height": user_profile.height,
                "weight": user_profile.weight,
                "activityLevel": user_profile.activityLevel,
                "bmi": user_profile.bmi,
                "bmr": user_profile.bmr,
                "tdee": user_profile.tdee
            },

            "periodCycle": {
                "hasPeriods": user_profile.hasPeriods,
                "lastPeriodDate": user_profile.lastPeriodDate,
                "cycleLength": user_profile.cycleLength,
                "cycleLengthRegular": user_profile.cycleLengthRegular,
                "pregnancyStatus": user_profile.pregnancyStatus,
                "trackingPreference": user_profile.periodTrackingPreference,
            } if user_profile.gender and user_profile.gender.lower() == 'female' else {},
            
            "primaryGoal": user_profile.primaryGoal,
            "weightGoal": {
                "weightGoal": user_profile.weightGoal,
                "targetWeight": user_profile.targetWeight,
                "timeline": user_profile.goalTimeline
            },
            "sleepInfo": {
                "sleepHours": user_profile.sleepHours,
                "bedtime": user_profile.bedtime,
                "wakeupTime": user_profile.wakeupTime,
                "sleepIssues": user_profile.sleepIssues
            },
            "dietaryPreferences": {
                "dietaryPreferences": user_profile.dietaryPreferences,
                "waterIntake": user_profile.waterIntake,
                "medicalConditions": user_profile.medicalConditions,
                "otherCondition": user_profile.otherMedicalCondition
            },
            "workoutPreferences": {
                "workoutTypes": user_profile.preferredWorkouts,
                "frequency": user_profile.workoutFrequency,
                "duration": user_profile.workoutDuration
            },
            "exerciseSetup": {
                "workoutLocation": user_profile.workoutLocation,
                "equipment": user_profile.availableEquipment,
                "fitnessLevel": user_profile.fitnessLevel,
                "hasTrainer": user_profile.hasTrainer
            }
        }
        
        # Check if user already exists
        existing_user = await get_user_by_email(user_profile.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create user using unified backend
        user_id = await create_user_from_onboarding(onboarding_data)
        
        return HealthUserResponse(success=True, userId=user_id)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating health user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/onboarding/complete", response_model=HealthUserResponse)
async def complete_flutter_onboarding(onboarding_data: UnifiedOnboardingRequest):
    """Complete onboarding process for Flutter app using unified format"""
    try:
        print("🔍 DEBUGGING ONBOARDING DATA RECEIVED:")
        print(f"📧 Email: {onboarding_data.basicInfo.get('email')}")
        print(f"⚧ Gender: {onboarding_data.basicInfo.get('gender')}")
        
        # ADD THIS DEBUGGING FOR PERIOD CYCLE DATA
        if hasattr(onboarding_data, 'periodCycle') and onboarding_data.periodCycle:
            print(f"🌸 Period cycle data received:")
            print(f"  hasPeriods: {onboarding_data.periodCycle.get('hasPeriods')}")
            print(f"  lastPeriodDate: {onboarding_data.periodCycle.get('lastPeriodDate')}")
            print(f"  cycleLength: {onboarding_data.periodCycle.get('cycleLength')}")
            print(f"  cycleLengthRegular: {onboarding_data.periodCycle.get('cycleLengthRegular')}")
            print(f"  pregnancyStatus: {onboarding_data.periodCycle.get('pregnancyStatus')}")
            print(f"  trackingPreference: {onboarding_data.periodCycle.get('trackingPreference')}")
        else:
            print("❌ No period cycle data received")
            
        print(f"📦 Full onboarding data: {onboarding_data.dict()}")
        
        # Check if user already exists
        email = onboarding_data.basicInfo.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
            
        existing_user = await get_user_by_email(email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create user using unified backend
        user_id = await create_user_from_onboarding(onboarding_data.dict())
        
        return HealthUserResponse(
            success=True, 
            userId=user_id,
            message="Onboarding completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing Flutter onboarding: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/login", response_model=HealthUserResponse)
async def login_health_user(login_data: HealthLoginRequest):
    """Login for mobile app users using unified backend"""
    try:
        # Get user by email
        user = await get_user_by_email(login_data.email)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        password_to_verify = user.password_hash or user.password
        if not verify_password(login_data.password, password_to_verify):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return HealthUserResponse(success=True, userId=str(user.id))
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during health user login: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/users/{user_id}", response_model=HealthUserResponse)
async def get_health_user_profile(user_id: str):
    """Get user profile for mobile app using unified backend"""
    try:
        user_profile = await get_user_profile(user_id)
        
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Format for Flutter app compatibility - ADD PERIOD CYCLE FIELDS
        flutter_profile = {
            'id': user_profile.get('id', ''),
            'name': user_profile.get('name', ''),
            'email': user_profile.get('email', ''),
            'gender': user_profile.get('gender', ''),
            'age': user_profile.get('age', 0),
            'height': user_profile.get('height', 0.0),
            'weight': user_profile.get('weight', 0.0),
            'activityLevel': user_profile.get('activityLevel', ''),
            
            'hasPeriods': user_profile.get('hasPeriods') or user_profile.get('has_periods'),
            'lastPeriodDate': user_profile.get('lastPeriodDate') or user_profile.get('last_period_date'),
            'cycleLength': user_profile.get('cycleLength') or user_profile.get('cycle_length'),
            'cycleLengthRegular': user_profile.get('cycleLengthRegular') or user_profile.get('cycle_length_regular'),
            'pregnancyStatus': user_profile.get('pregnancyStatus') or user_profile.get('pregnancy_status'),
            'periodTrackingPreference': user_profile.get('periodTrackingPreference') or user_profile.get('period_tracking_preference'),
            
            'primaryGoal': user_profile.get('primaryGoal', ''),
            'weightGoal': user_profile.get('weightGoal', ''),
            'targetWeight': user_profile.get('targetWeight', 0.0),
            'goalTimeline': user_profile.get('goalTimeline', ''),
            'sleepHours': user_profile.get('sleepHours', 7.0),
            'bedtime': user_profile.get('bedtime', ''),
            'wakeupTime': user_profile.get('wakeupTime', ''),
            'sleepIssues': user_profile.get('sleepIssues', []),
            'dietaryPreferences': user_profile.get('dietaryPreferences', []),
            'waterIntake': user_profile.get('waterIntake', 2.0),
            'medicalConditions': user_profile.get('medicalConditions', []),
            'otherMedicalCondition': user_profile.get('otherMedicalCondition', ''),
            'preferredWorkouts': user_profile.get('preferredWorkouts', []),
            'workoutFrequency': user_profile.get('workoutFrequency', 3),
            'workoutDuration': user_profile.get('workoutDuration', 30),
            'workoutLocation': user_profile.get('workoutLocation', ''),
            'availableEquipment': user_profile.get('availableEquipment', []),
            'fitnessLevel': user_profile.get('fitnessLevel', 'Beginner'),
            'hasTrainer': user_profile.get('hasTrainer', False),
            'formData': {
                'bmi': user_profile.get('bmi', 0.0),
                'bmr': user_profile.get('bmr', 0.0),
                'tdee': user_profile.get('tdee', 0.0),
            }
        }
        
        return HealthUserResponse(success=True, userProfile=flutter_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching health user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Additional endpoints for Flutter-specific features
@health_router.post("/water-intake")
async def log_water_intake(water_data: WaterIntakeRequest):
    """Log water intake for mobile app"""
    try:
        # Implement water intake logging logic here
        # This would typically save to a separate water_intake table
        return {"success": True, "message": "Water intake logged successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/meals")
async def log_meal(meal_data: MealRequest):
    """Log meal for mobile app"""
    try:
        # Implement meal logging logic here
        # This would typically save to a separate meals table
        return {"success": True, "message": "Meal logged successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))