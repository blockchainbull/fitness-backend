# flutter_routes.py - Updated to use unified backend
from fastapi import APIRouter, HTTPException
import traceback
import uuid
from flutter_models import (
    HealthUserCreate, HealthUserResponse, HealthLoginRequest, 
    WaterIntakeRequest, MealRequest, UnifiedOnboardingRequest
)
from database import create_user_from_onboarding, get_user_by_email, verify_password, get_user_profile, get_health_db_cursor
from datetime import datetime, timedelta

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
    
# Supplement logging functions
@health_router.post("/supplements/preferences")
async def save_supplement_preferences(request_data: dict):
    """Save user's supplement preferences"""
    try:
        user_id = request_data.get('user_id')
        supplements = request_data.get('supplements', [])
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        with get_health_db_cursor() as (conn, cursor):
            # Clear existing preferences (if you want this table)
            # For now, let's just use the supplement_tracking table
            
            # Return success
            return {
                "success": True, 
                "message": f"Supplement preferences saved for {len(supplements)} supplements"
            }
        
    except Exception as e:
        print(f"Error saving supplement preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to save preferences")

@health_router.post("/supplements/log")
async def log_supplement_intake(log_data: dict):
    """Log daily supplement intake"""
    try:
        print(f"🔍 Received supplement log data: {log_data}")
        
        user_id = log_data.get('user_id')
        date_str = log_data.get('date')  # Format: 'YYYY-MM-DD'
        supplement_name = log_data.get('supplement_name')
        taken = log_data.get('taken', False)
        dosage = log_data.get('dosage')
        time_taken_str = log_data.get('time_taken')
        
        print(f"📝 Logging: user={user_id}, date={date_str}, supplement={supplement_name}, taken={taken}")
        
        if not all([user_id, date_str, supplement_name]):
            print(f"❌ Missing required fields: user_id={user_id}, date={date_str}, supplement_name={supplement_name}")
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Parse the date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        print(f"📅 Parsed date: {date_obj}")
        
        # Parse time_taken if provided
        time_taken_obj = None
        if time_taken_str and taken:
            try:
                time_taken_obj = datetime.fromisoformat(time_taken_str.replace('Z', '+00:00'))
            except:
                time_taken_obj = datetime.now()
        
        with get_health_db_cursor() as (conn, cursor):
            # Check if record exists
            cursor.execute("""
                SELECT id FROM supplement_tracking 
                WHERE user_id = %s AND date = %s AND supplement_name = %s
            """, (user_id, date_obj, supplement_name))
            
            existing = cursor.fetchone()
            print(f"🔍 Existing record: {existing}")
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE supplement_tracking 
                    SET taken = %s, time_taken = %s, dosage = %s
                    WHERE user_id = %s AND date = %s AND supplement_name = %s
                """, (taken, time_taken_obj, dosage, user_id, date_obj, supplement_name))
                print(f"✅ Updated supplement log: {supplement_name} = {taken} on {date_str}")
            else:
                # Insert new record
                new_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO supplement_tracking (
                        id, user_id, date, supplement_name, dosage, taken, time_taken, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_id,
                    user_id,
                    date_obj,
                    supplement_name,
                    dosage,
                    taken,
                    time_taken_obj,
                    datetime.now()
                ))
                print(f"✅ Inserted supplement log: {supplement_name} = {taken} on {date_str} with ID {new_id}")
            
            conn.commit()
            print("💾 Database transaction committed")
            
        return {"success": True, "message": "Supplement intake logged"}
        
    except Exception as e:
        print(f"❌ Error logging supplement intake: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to log supplement intake")

@health_router.get("/supplements/status/{user_id}")
async def get_todays_supplement_status(user_id: str):
    """Get today's supplement status for user"""
    try:
        today = datetime.now().date()
        
        with get_health_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT supplement_name, taken FROM supplement_tracking 
                WHERE user_id = %s AND date = %s
            """, (user_id, today))
            
            records = cursor.fetchall()
            
        # Convert to dictionary
        status = {}
        for record in records:
            status[record['supplement_name']] = record['taken']
            
        return {
            "success": True,
            "status": status,
            "date": today.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        print(f"Error getting supplement status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supplement status")

@health_router.get("/supplements/history/{user_id}")
async def get_supplement_history(user_id: str, days: int = 30):
    """Get supplement intake history"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        with get_health_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT * FROM supplement_tracking 
                WHERE user_id = %s AND date >= %s
                ORDER BY date DESC, supplement_name ASC
            """, (user_id, start_date.date()))
            
            records = cursor.fetchall()
            
        # Convert records to list of dictionaries
        history = []
        for record in records:
            history.append({
                'id': str(record['id']),
                'user_id': str(record['user_id']),
                'date': record['date'].strftime('%Y-%m-%d'),
                'supplement_name': record['supplement_name'],
                'dosage': record['dosage'],
                'taken': record['taken'],
                'time_taken': record['time_taken'].isoformat() if record['time_taken'] else None,
                'created_at': record['created_at'].isoformat() if record['created_at'] else None,
            })
            
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        print(f"Error getting supplement history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supplement history")
    
@health_router.get("/supplements/test")
async def test_supplement_db():
    """Test supplement database connectivity"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            # Test basic query
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            # Check if supplement_tracking table exists
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'supplement_tracking'
            """)
            table_exists = cursor.fetchone()
            
            # Count existing records
            cursor.execute("SELECT COUNT(*) as count FROM supplement_tracking")
            count_result = cursor.fetchone()
            
        return {
            "success": True,
            "database_connection": "OK",
            "test_query": result['test'] if result else None,
            "table_exists": table_exists is not None,
            "record_count": count_result['count'] if count_result else 0
        }
        
    except Exception as e:
        print(f"Database test error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    
# User Supplement Preferences functions
@health_router.post("/supplements/preferences")
async def save_supplement_preferences(request_data: dict):
    """Save user's supplement preferences"""
    try:
        user_id = request_data.get('user_id')
        supplements = request_data.get('supplements', [])
        
        print(f"🔍 Saving supplement preferences for user: {user_id}")
        print(f"📝 Supplements to save: {len(supplements)} items")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        with get_health_db_cursor() as (conn, cursor):
            # Clear existing preferences for this user
            cursor.execute("""
                DELETE FROM user_supplement_preferences 
                WHERE user_id = %s
            """, (user_id,))
            print(f"🗑️ Cleared existing preferences for user: {user_id}")
            
            # Insert new preferences
            for supplement in supplements:
                new_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO user_supplement_preferences (
                        id, user_id, supplement_name, dosage, frequency, 
                        preferred_time, notes, is_active, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_id,
                    user_id,
                    supplement.get('name'),
                    supplement.get('dosage'),
                    supplement.get('frequency', 'Daily'),
                    supplement.get('preferred_time', '9:00 AM'),
                    supplement.get('notes', ''),
                    True,  # is_active
                    datetime.now(),
                    datetime.now()
                ))
                print(f"✅ Saved preference: {supplement.get('name')} - {supplement.get('dosage')}")
            
            conn.commit()
            print(f"💾 Committed {len(supplements)} supplement preferences to database")
            
            return {
                "success": True, 
                "message": f"Saved {len(supplements)} supplement preferences",
                "user_id": user_id,
                "count": len(supplements)
            }
        
    except Exception as e:
        print(f"❌ Error saving supplement preferences: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to save supplement preferences")

@health_router.get("/supplements/preferences/{user_id}")
async def get_supplement_preferences(user_id: str):
    """Get user's supplement preferences"""
    try:
        print(f"🔍 Getting supplement preferences for user: {user_id}")
        
        with get_health_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT * FROM user_supplement_preferences 
                WHERE user_id = %s AND is_active = true
                ORDER BY created_at ASC
            """, (user_id,))
            
            preferences = cursor.fetchall()
            print(f"📊 Found {len(preferences)} supplement preferences")
            
        # Convert to list of dictionaries
        preferences_list = []
        for pref in preferences:
            preferences_list.append({
                'id': str(pref['id']),
                'user_id': str(pref['user_id']),
                'supplement_name': pref['supplement_name'],
                'dosage': pref['dosage'],
                'frequency': pref['frequency'],
                'preferred_time': pref['preferred_time'],
                'notes': pref['notes'],
                'is_active': pref['is_active'],
                'created_at': pref['created_at'].isoformat() if pref['created_at'] else None,
                'updated_at': pref['updated_at'].isoformat() if pref['updated_at'] else None,
            })
            
        return {
            "success": True,
            "preferences": preferences_list,
            "count": len(preferences_list)
        }
        
    except Exception as e:
        print(f"❌ Error getting supplement preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supplement preferences")