# flutter_routes.py - Updated to use unified backend
from fastapi import APIRouter, HTTPException
import traceback
import uuid
from flutter_models import HealthUserCreate, HealthUserResponse, HealthLoginRequest, UnifiedOnboardingRequest
from database import create_user_from_onboarding, get_user_by_email, verify_password, get_user_profile, get_health_db_cursor, WaterEntryCreate
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from database import SessionLocal, PeriodTracking
from database import StepEntryCreate, StepEntryResponse

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
                "periodLength": user_profile.periodLength if hasattr(user_profile, 'periodLength') else 5,
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

@health_router.post("/auth/login")
async def login_user(login_data: dict):
    """Login endpoint for mobile app"""
    try:
        email = login_data.get('email')
        password = login_data.get('password')
        
        print(f"🔐 Login attempt for: {email}")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
        
        # Get user by email
        user = await get_user_by_email(email)
        if not user:
            print(f"❌ User not found: {email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not verify_password(password, user.password):
            print(f"❌ Invalid password for: {email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        print(f"✅ Login successful for: {email}")
        
        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "age": user.age,
                "gender": user.gender,
                "height": user.height,
                "weight": user.weight,
                "activity_level": user.activity_level,
                "bmi": user.bmi,
                "bmr": user.bmr,
                "tdee": user.tdee
            },
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Supplement logging endpoints
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
    
# User Supplement Preferences endpoints
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
            # Instead of deleting all, use upsert logic
            for supplement in supplements:
                # Check if this supplement preference already exists
                cursor.execute("""
                    SELECT id FROM user_supplement_preferences 
                    WHERE user_id = %s AND supplement_name = %s
                """, (user_id, supplement.get('name')))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing preference
                    cursor.execute("""
                        UPDATE user_supplement_preferences 
                        SET dosage = %s, frequency = %s, preferred_time = %s, 
                            notes = %s, updated_at = %s
                        WHERE user_id = %s AND supplement_name = %s
                    """, (
                        supplement.get('dosage'),
                        supplement.get('frequency', 'Daily'),
                        supplement.get('preferred_time', '9:00 AM'),
                        supplement.get('notes', ''),
                        datetime.now(),
                        user_id,
                        supplement.get('name')
                    ))
                    print(f"🔄 Updated preference: {supplement.get('name')}")
                else:
                    # Insert new preference
                    cursor.execute("""
                        INSERT INTO user_supplement_preferences (
                            id, user_id, supplement_name, dosage, frequency, 
                            preferred_time, notes, is_active, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        uuid.uuid4(),
                        uuid.UUID(user_id),  
                        supplement.get('name'),
                        supplement.get('dosage'),
                        supplement.get('frequency', 'Daily'),
                        supplement.get('preferred_time', '9:00 AM'),
                        supplement.get('notes', ''),
                        True,  # is_active
                        datetime.now(),
                        datetime.now()
                    ))
                    print(f"✅ Inserted new preference: {supplement.get('name')}")
            
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
        print(f"🔍 User ID type: {type(user_id)}")
        print(f"🔍 User ID length: {len(user_id)}")
        
        with get_health_db_cursor() as (conn, cursor):
            # First, check what user IDs exist in the database
            cursor.execute("""
                SELECT DISTINCT user_id FROM user_supplement_preferences LIMIT 5
            """)
            existing_users = cursor.fetchall()
            print(f"🔍 Existing user IDs in database: {[str(u['user_id']) for u in existing_users]}")
            
            # Now try the actual query
            cursor.execute("""
                SELECT * FROM user_supplement_preferences 
                WHERE user_id = %s AND is_active = true
                ORDER BY created_at ASC
            """, (user_id,))
            
            preferences = cursor.fetchall()
            print(f"📊 Found {len(preferences)} supplement preferences for user: {user_id}")
            
            if len(preferences) == 0:
                # Try with UUID conversion
                try:
                    import uuid as uuid_module
                    user_uuid = uuid_module.UUID(user_id)
                    cursor.execute("""
                        SELECT * FROM user_supplement_preferences 
                        WHERE user_id = %s AND is_active = true
                        ORDER BY created_at ASC
                    """, (user_uuid,))
                    
                    preferences_uuid = cursor.fetchall()
                    print(f"📊 Found {len(preferences_uuid)} preferences using UUID conversion")
                    
                    if len(preferences_uuid) > 0:
                        preferences = preferences_uuid
                        print("✅ UUID conversion worked!")
                        
                except Exception as e:
                    print(f"❌ UUID conversion failed: {e}")
            
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
            "count": len(preferences_list),
            "debug_info": {
                "queried_user_id": user_id,
                "existing_users": [str(u['user_id']) for u in existing_users] if 'existing_users' in locals() else []
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting supplement preferences: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to get supplement preferences")
    
# Water Logging Endpoints
@health_router.post("/water")
async def save_water_entry(water_data: WaterEntryCreate):
    """Save or update daily water intake"""
    try:
        print(f"💧 Saving water entry: {water_data.glasses_consumed} glasses for user {water_data.user_id}")
        
        with get_health_db_cursor() as (conn, cursor):
            # Parse date
            try:
                entry_date = datetime.fromisoformat(water_data.date.replace('Z', '+00:00'))
                if entry_date.tzinfo is None:
                    entry_date = entry_date.replace(tzinfo=timezone.utc)
            except ValueError:
                entry_date = datetime.now(timezone.utc)
            
            # Check if entry exists for this date
            cursor.execute("""
                SELECT id FROM daily_water 
                WHERE user_id = %s AND date::date = %s::date
            """, (water_data.user_id, entry_date.date()))
            
            existing_entry = cursor.fetchone()
            
            if existing_entry:
                # Update existing entry
                cursor.execute("""
                    UPDATE daily_water 
                    SET glasses_consumed = %s, total_ml = %s, target_ml = %s, 
                        notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND date::date = %s::date
                    RETURNING id
                """, (
                    water_data.glasses_consumed, water_data.total_ml, water_data.target_ml,
                    water_data.notes, water_data.user_id, entry_date.date()
                ))
            else:
                # Create new entry
                entry_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO daily_water 
                    (id, user_id, date, glasses_consumed, total_ml, target_ml, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    entry_id, water_data.user_id, entry_date, 
                    water_data.glasses_consumed, water_data.total_ml, 
                    water_data.target_ml, water_data.notes
                ))
            
            result = cursor.fetchone()
            saved_id = result['id']
            
            print(f"✅ Water entry saved with ID: {saved_id}")
            return {"success": True, "id": saved_id}
            
    except Exception as e:
        print(f"❌ Error saving water entry: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/water/{user_id}")
async def get_water_history(user_id: str, limit: int = 30):
    """Get water intake history for a user"""
    try:
        print(f"💧 Getting water history for user: {user_id}")
        
        with get_health_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT * FROM daily_water 
                WHERE user_id = %s 
                ORDER BY date DESC 
                LIMIT %s
            """, (user_id, limit))
            
            entries = cursor.fetchall()
            
            water_entries = []
            for entry in entries:
                water_entries.append({
                    'id': str(entry['id']),
                    'user_id': str(entry['user_id']),
                    'date': entry['date'].isoformat(),
                    'glasses_consumed': entry['glasses_consumed'],
                    'total_ml': float(entry['total_ml']),
                    'target_ml': float(entry['target_ml']),
                    'notes': entry['notes'],
                    'created_at': entry['created_at'].isoformat() if entry['created_at'] else None,
                    'updated_at': entry['updated_at'].isoformat() if entry['updated_at'] else None,
                })
            
            print(f"✅ Retrieved {len(water_entries)} water entries")
            return {"success": True, "entries": water_entries}
            
    except Exception as e:
        print(f"❌ Error getting water history: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/water/{user_id}/today")
async def get_today_water(user_id: str):
    """Get today's water intake"""
    try:
        print(f"💧 Getting today's water for user: {user_id}")
        
        with get_health_db_cursor() as (conn, cursor):
            today = datetime.now(timezone.utc).date()
            
            cursor.execute("""
                SELECT * FROM daily_water 
                WHERE user_id = %s AND date::date = %s
            """, (user_id, today))
            
            entry = cursor.fetchone()
            
            if entry:
                water_entry = {
                    'id': str(entry['id']),
                    'user_id': str(entry['user_id']),
                    'date': entry['date'].isoformat(),
                    'glasses_consumed': entry['glasses_consumed'],
                    'total_ml': float(entry['total_ml']),
                    'target_ml': float(entry['target_ml']),
                    'notes': entry['notes'],
                    'created_at': entry['created_at'].isoformat() if entry['created_at'] else None,
                    'updated_at': entry['updated_at'].isoformat() if entry['updated_at'] else None,
                }
                return {"success": True, "entry": water_entry}
            else:
                return {"success": True, "entry": None}
                
    except Exception as e:
        print(f"❌ Error getting today's water: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
#Period Logging endpoints
@health_router.post("/period")
async def save_period_entry(request: dict):
    """Save or update period entry"""
    async with SessionLocal() as session:
        try:
            period_id = request.get('id')
            if not period_id:
                period_id = str(uuid.uuid4())
            else:
                # Try to parse as UUID if it's a string
                try:
                    period_id = str(uuid.UUID(period_id))
                except:
                    period_id = str(uuid.uuid4())
            
            # Check if entry exists
            existing = await session.execute(
                select(PeriodTracking).where(PeriodTracking.id == uuid.UUID(period_id))
            )
            existing_entry = existing.scalars().first()
            
            if existing_entry:
                # Update existing
                if request.get('end_date'):
                    existing_entry.end_date = datetime.fromisoformat(request['end_date'].replace('Z', '+00:00'))
                existing_entry.flow_intensity = request.get('flow_intensity', existing_entry.flow_intensity)
                existing_entry.symptoms = request.get('symptoms', existing_entry.symptoms)
                existing_entry.mood = request.get('mood', existing_entry.mood)
                existing_entry.notes = request.get('notes', existing_entry.notes)
            else:
                # Create new
                new_entry = PeriodTracking(
                    id=uuid.UUID(period_id),
                    user_id=uuid.UUID(request['user_id']),
                    start_date=datetime.fromisoformat(request['start_date'].replace('Z', '+00:00')),
                    end_date=datetime.fromisoformat(request['end_date'].replace('Z', '+00:00')) if request.get('end_date') else None,
                    flow_intensity=request.get('flow_intensity', 'Medium'),
                    symptoms=request.get('symptoms', []),
                    mood=request.get('mood'),
                    notes=request.get('notes')
                )
                session.add(new_entry)
            
            await session.commit()
            return {"id": str(period_id), "status": "success"}
            
        except Exception as e:
            await session.rollback()
            print(f"Error saving period entry: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=str(e))

@health_router.get("/period/{user_id}") 
async def get_period_history(user_id: str, limit: int = 12):
    """Get period history for user"""
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(PeriodTracking)
                .where(PeriodTracking.user_id == uuid.UUID(user_id))
                .order_by(PeriodTracking.start_date.desc())
                .limit(limit)
            )
            
            entries = result.scalars().all()
            return [
                {
                    "id": str(entry.id),
                    "user_id": str(entry.user_id),
                    "start_date": entry.start_date.isoformat() if entry.start_date else None,
                    "end_date": entry.end_date.isoformat() if entry.end_date else None,
                    "flow_intensity": entry.flow_intensity,
                    "symptoms": entry.symptoms or [],
                    "mood": entry.mood,
                    "notes": entry.notes,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None
                }
                for entry in entries
            ]
            
        except Exception as e:
            print(f"Error fetching period history: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=str(e))

@health_router.get("/period/{user_id}/current")
async def get_current_period(user_id: str):
    """Get current active period for user"""
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(PeriodTracking)
                .where(
                    and_(
                        PeriodTracking.user_id == uuid.UUID(user_id),
                        PeriodTracking.end_date == None
                    )
                )
                .order_by(PeriodTracking.start_date.desc())
                .limit(1)
            )
            
            entry = result.scalars().first()
            
            if entry:
                return {
                    "id": str(entry.id),
                    "user_id": str(entry.user_id),
                    "start_date": entry.start_date.isoformat() if entry.start_date else None,
                    "end_date": None,
                    "flow_intensity": entry.flow_intensity,
                    "symptoms": entry.symptoms or [],
                    "mood": entry.mood,
                    "notes": entry.notes,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None
                }
            else:
                return None
            
        except Exception as e:
            print(f"Error fetching current period: {e}")
            raise HTTPException(status_code=400, detail=str(e))

@health_router.delete("/period/{entry_id}")
async def delete_period_entry(entry_id: str):
    """Delete a period entry"""
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(PeriodTracking).where(PeriodTracking.id == uuid.UUID(entry_id))
            )
            entry = result.scalars().first()
            
            if not entry:
                raise HTTPException(status_code=404, detail="Period entry not found")
            
            await session.delete(entry)
            await session.commit()
            
            return {"status": "success", "message": "Period entry deleted"}
            
        except Exception as e:
            await session.rollback()
            print(f"Error deleting period entry: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        
#step Logging endpoints
@health_router.get("/steps/{user_id}/today")
async def get_today_steps(user_id: str):
    """Get today's step entry for a user"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            today = datetime.now().date()
            
            cursor.execute("""
                SELECT id, user_id, date, steps, goal, calories_burned, 
                       distance_km, active_minutes, source_type, last_synced,
                       created_at, updated_at
                FROM daily_steps 
                WHERE user_id = %s AND date::date = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id, today))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    "id": str(result['id']),
                    "userId": str(result['user_id']),
                    "date": result['date'].strftime('%Y-%m-%d') if hasattr(result['date'], 'strftime') else str(result['date']),
                    "steps": result['steps'] or 0,
                    "goal": result['goal'] or 10000,
                    "caloriesBurned": result['calories_burned'] or 0.0,
                    "distanceKm": result['distance_km'] or 0.0,
                    "activeMinutes": result['active_minutes'] or 0,
                    "sourceType": result['source_type'] or "manual",
                    "lastSynced": result['last_synced'].isoformat() if result['last_synced'] else None,
                    "createdAt": result['created_at'].isoformat(),
                    "updatedAt": result['updated_at'].isoformat() if result['updated_at'] else result['created_at'].isoformat()
                }
            
            return None
            
    except Exception as e:
        print(f"Error getting today's steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/steps/{user_id}/range")
async def get_steps_in_range(
    user_id: str, 
    start: str,  # ISO date string
    end: str     # ISO date string
):
    """Get step entries for a date range"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            start_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date()
            end_date = datetime.fromisoformat(end.replace('Z', '+00:00')).date()
            
            cursor.execute("""
                SELECT id, user_id, date, steps, goal, calories_burned, 
                       distance_km, active_minutes, source_type, last_synced,
                       created_at, updated_at
                FROM daily_steps 
                WHERE user_id = %s AND date::date BETWEEN %s AND %s
                ORDER BY date DESC
            """, (user_id, start_date, end_date))
            
            results = cursor.fetchall()
            
            step_entries = []
            for result in results:
                step_entries.append({
                    "id": str(result['id']),
                    "userId": str(result['user_id']),
                    "date": result['date'].strftime('%Y-%m-%d') if hasattr(result['date'], 'strftime') else str(result['date']),
                    "steps": result['steps'] or 0,
                    "goal": result['goal'] or 10000,
                    "caloriesBurned": result['calories_burned'] or 0.0,
                    "distanceKm": result['distance_km'] or 0.0,
                    "activeMinutes": result['active_minutes'] or 0,
                    "sourceType": result['source_type'] or "manual",
                    "lastSynced": result['last_synced'].isoformat() if result['last_synced'] else None,
                    "createdAt": result['created_at'].isoformat(),
                    "updatedAt": result['updated_at'].isoformat() if result['updated_at'] else result['created_at'].isoformat()
                })
            
            return step_entries
            
    except Exception as e:
        print(f"Error getting steps in range: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/steps")
async def save_step_entry(step_data: StepEntryCreate):
    """Save or update a step entry"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            entry_date = datetime.fromisoformat(step_data.date.replace('Z', '+00:00'))
            now = datetime.now()
            
            # Check if entry exists for this date
            cursor.execute("""
                SELECT id FROM daily_steps 
                WHERE user_id = %s AND date::date = %s
            """, (step_data.userId, entry_date.date()))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing entry
                cursor.execute("""
                    UPDATE daily_steps 
                    SET steps = %s, goal = %s, calories_burned = %s, 
                        distance_km = %s, active_minutes = %s, 
                        source_type = %s, last_synced = %s, updated_at = %s
                    WHERE user_id = %s AND date::date = %s
                """, (
                    step_data.steps, step_data.goal, step_data.caloriesBurned,
                    step_data.distanceKm, step_data.activeMinutes,
                    step_data.sourceType, now, now,
                    step_data.userId, entry_date.date()
                ))
                print(f"✅ Updated step entry for {step_data.userId} on {entry_date.date()}")
            else:
                # Create new entry
                new_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO daily_steps 
                    (id, user_id, date, steps, goal, calories_burned, distance_km, 
                     active_minutes, source_type, last_synced, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_id, step_data.userId, entry_date, step_data.steps, step_data.goal,
                    step_data.caloriesBurned, step_data.distanceKm, step_data.activeMinutes,
                    step_data.sourceType, now, now, now
                ))
                print(f"✅ Created new step entry for {step_data.userId} on {entry_date.date()} with ID {new_id}")
            
            conn.commit()
            return {"success": True, "message": "Step entry saved successfully"}
            
    except Exception as e:
        print(f"Error saving step entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/steps/{user_id}")
async def get_all_steps(user_id: str, limit: int = 100):
    """Get all step entries for a user (with optional limit)"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT id, user_id, date, steps, goal, calories_burned, 
                       distance_km, active_minutes, source_type, last_synced,
                       created_at, updated_at
                FROM daily_steps 
                WHERE user_id = %s
                ORDER BY date DESC
                LIMIT %s
            """, (user_id, limit))
            
            results = cursor.fetchall()
            
            step_entries = []
            for result in results:
                step_entries.append({
                    "id": str(result['id']),
                    "userId": str(result['user_id']),
                    "date": result['date'].strftime('%Y-%m-%d') if hasattr(result['date'], 'strftime') else str(result['date']),
                    "steps": result['steps'] or 0,
                    "goal": result['goal'] or 10000,
                    "caloriesBurned": result['calories_burned'] or 0.0,
                    "distanceKm": result['distance_km'] or 0.0,
                    "activeMinutes": result['active_minutes'] or 0,
                    "sourceType": result['source_type'] or "manual",
                    "lastSynced": result['last_synced'].isoformat() if result['last_synced'] else None,
                    "createdAt": result['created_at'].isoformat(),
                    "updatedAt": result['updated_at'].isoformat() if result['updated_at'] else result['created_at'].isoformat()
                })
            
            return step_entries
            
    except Exception as e:
        print(f"Error getting all steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@health_router.delete("/steps/{user_id}/{date}")
async def delete_step_entry(user_id: str, date: str):
    """Delete a step entry for a specific date"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            entry_date = datetime.fromisoformat(date.replace('Z', '+00:00')).date()
            
            cursor.execute("""
                DELETE FROM daily_steps 
                WHERE user_id = %s AND date::date = %s
            """, (user_id, entry_date))
            
            conn.commit()
            return {"success": True, "message": "Step entry deleted successfully"}
            
    except Exception as e:
        print(f"Error deleting step entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/steps/{user_id}/stats")
async def get_step_stats(user_id: str, days: int = 30):
    """Get step statistics for the last N days"""
    try:
        with get_health_db_cursor() as (conn, cursor):
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get basic stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_days,
                    SUM(steps) as total_steps,
                    AVG(steps) as avg_steps,
                    MAX(steps) as max_steps,
                    MIN(steps) as min_steps,
                    SUM(CASE WHEN steps >= goal THEN 1 ELSE 0 END) as goals_achieved,
                    SUM(calories_burned) as total_calories,
                    SUM(distance_km) as total_distance,
                    SUM(active_minutes) as total_active_minutes
                FROM daily_steps 
                WHERE user_id = %s AND date::date BETWEEN %s AND %s
            """, (user_id, start_date, end_date))
            
            stats = cursor.fetchone()
            
            if stats and stats['total_days'] > 0:  # If we have data
                return {
                    "period_days": days,
                    "total_days": stats['total_days'],
                    "total_steps": stats['total_steps'] or 0,
                    "avg_steps": round(stats['avg_steps'] or 0),
                    "max_steps": stats['max_steps'] or 0,
                    "min_steps": stats['min_steps'] or 0,
                    "goals_achieved": stats['goals_achieved'] or 0,
                    "goal_achievement_rate": round((stats['goals_achieved'] or 0) / stats['total_days'] * 100, 1),
                    "total_calories": round(stats['total_calories'] or 0, 1),
                    "total_distance": round(stats['total_distance'] or 0, 2),
                    "total_active_minutes": stats['total_active_minutes'] or 0
                }
            else:
                return {
                    "period_days": days,
                    "total_days": 0,
                    "total_steps": 0,
                    "avg_steps": 0,
                    "max_steps": 0,
                    "min_steps": 0,
                    "goals_achieved": 0,
                    "goal_achievement_rate": 0,
                    "total_calories": 0,
                    "total_distance": 0,
                    "total_active_minutes": 0
                }
            
    except Exception as e:
        print(f"Error getting step stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))