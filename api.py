"""
API routes for the nutrition and exercise coach application.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from models import PromptRequest, ConversationResponse
from database import create_user_from_onboarding, get_user_by_email, verify_password, get_user_profile, SessionLocal
from agent import get_agent_response
from sqlalchemy.orm import Session
from sqlalchemy import select
from passlib.context import CryptContext
import traceback
from datetime import datetime, timezone
from database import User


router = APIRouter()

class UserUpdateRequest(BaseModel):
    """
    Pydantic model for user profile updates.
    Excludes readonly fields: name, email, age, gender
    """
    # Physical stats (editable)
    height: Optional[float] = Field(None, ge=0, le=300, description="Height in cm")
    weight: Optional[float] = Field(None, ge=0, le=1000, description="Weight in kg")
    activity_level: Optional[str] = Field(None, pattern="^(Sedentary|Lightly active|Moderately active|Very active|Extra active)$")
    
    # Goals and preferences (editable)
    primary_goal: Optional[str] = None
    fitness_goal: Optional[str] = None
    weight_goal: Optional[str] = Field(None, pattern="^(lose_weight|gain_weight|maintain_weight)$")
    target_weight: Optional[float] = Field(None, ge=0, le=1000)
    goal_timeline: Optional[str] = None
    
    # Sleep preferences (editable)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    bedtime: Optional[str] = None
    wakeup_time: Optional[str] = None
    sleep_issues: Optional[list] = None
    
    # Nutrition preferences (editable)
    dietary_preferences: Optional[list] = None
    water_intake: Optional[float] = Field(None, ge=0, le=20)
    medical_conditions: Optional[list] = None
    other_medical_condition: Optional[str] = None
    
    # Exercise preferences (editable)
    preferred_workouts: Optional[list] = None
    workout_frequency: Optional[int] = None
    workout_duration: Optional[int] = None
    workout_location: Optional[str] = None
    available_equipment: Optional[list] = None
    fitness_level: Optional[str] = None
    has_trainer: Optional[bool] = None
    
    # Additional preferences
    preferences: Optional[dict] = None

class UserResponse(BaseModel):
    """Response model for user data"""
    id: str
    name: str
    email: str
    age: Optional[int]
    gender: Optional[str]
    height: Optional[float]
    weight: Optional[float]
    activity_level: Optional[str]
    bmi: Optional[float]
    bmr: Optional[float]
    tdee: Optional[float]
    
    class Config:
        from_attributes = True


class OnboardingCompleteRequest(BaseModel):
    basicInfo: Optional[Dict[str, Any]] = {}
    primaryGoal: Optional[str] = ""
    weightGoal: Optional[Dict[str, Any]] = {}
    sleepInfo: Optional[Dict[str, Any]] = {}
    dietaryPreferences: Optional[Dict[str, Any]] = {}
    workoutPreferences: Optional[Dict[str, Any]] = {}
    exerciseSetup: Optional[Dict[str, Any]] = {}

class OnboardingCompleteResponse(BaseModel):
    success: bool
    userId: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    success: bool
    user: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None

async def get_db():
    async with SessionLocal() as session:
        yield session

def calculate_health_metrics(height: float, weight: float, age: int, gender: str, activity_level: str) -> dict:
    """Calculate BMI, BMR, and TDEE"""
    if not all([height, weight, age, gender]):
        return {'bmi': 0, 'bmr': 0, 'tdee': 0}
    
    # Calculate BMI
    height_m = height / 100  # Convert cm to meters
    bmi = weight / (height_m ** 2)
    
    # Calculate BMR using Mifflin-St Jeor Equation
    if gender.lower() == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:  # female
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Calculate TDEE based on activity level
    activity_multipliers = {
        'Sedentary': 1.2,
        'Lightly active': 1.375,
        'Moderately active': 1.55,
        'Very active': 1.725,
        'Extra active': 1.9,

        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    
    multiplier = activity_multipliers.get(activity_level, 1.2)
    tdee = bmr * multiplier
    
    return {
        'bmi': round(bmi, 1),
        'bmr': round(bmr, 0),
        'tdee': round(tdee, 0)
    }

@router.post("/api/onboarding/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(onboarding_data: OnboardingCompleteRequest):
    """Complete onboarding process for both web and Flutter applications"""
    try:
        print(f"Received onboarding data: {onboarding_data.dict()}")
        
        # Validate that we have basic info
        if not onboarding_data.basicInfo or not onboarding_data.basicInfo.get('email'):
            raise HTTPException(
                status_code=400, 
                detail="Basic information including email is required"
            )
        
        # Check if user already exists
        existing_user = await get_user_by_email(onboarding_data.basicInfo.get('email'))
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
        
        # Create user from onboarding data
        user_id = await create_user_from_onboarding(onboarding_data.dict())
        
        return OnboardingCompleteResponse(
            success=True,
            userId=user_id,
            message="Onboarding completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing onboarding: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete onboarding: {str(e)}"
        )

@router.post("/api/auth/login", response_model=LoginResponse)
async def login_user(login_data: LoginRequest):
    """Login endpoint for both web and Flutter applications"""
    try:
        print(f"🔐 Login attempt for email: {login_data.email}")
        
        # Get user by email
        user = await get_user_by_email(login_data.email)
        
        if not user:
            print(f"❌ No user found with email: {login_data.email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        print(f"✅ User found: {user.name} (ID: {user.id})")
        print(f"🔍 User has password: {bool(user.password)}")
        print(f"🔍 User has password_hash: {bool(user.password_hash)}")
        
        # Try both password fields for compatibility
        password_to_verify = user.password_hash or user.password
        
        if not password_to_verify:
            print(f"❌ No password found for user: {login_data.email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not verify_password(login_data.password, password_to_verify):
            print(f"❌ Password verification failed for: {login_data.email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        print(f"✅ Password verified for: {login_data.email}")
        
        # Get full user profile
        user_profile = await get_user_profile(str(user.id))
        
        print(f"✅ Login successful for: {login_data.email}")
        
        return LoginResponse(
            success=True,
            user=user_profile,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Unexpected error during login: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Login failed"
        )

@router.get("/api/user/profile/{user_id}")
async def get_user_profile_endpoint(user_id: str):
    """Get user profile endpoint for both applications"""
    try:
        user_profile = await get_user_profile(user_id)
        
        if not user_profile:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return {
            "success": True,
            "user": user_profile
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch user profile"
        )

# Keep existing conversation endpoints unchanged
@router.get("/get-conversation/{user_id}")
async def get_conversation(user_id: str):
    """Get conversation history for a user"""
    try:
        from database import get_user_conversation
        conversation = await get_user_conversation(user_id)
        return {"conversation": conversation}
    except Exception as e:
        print(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit-prompt")
async def submit_prompt(data: PromptRequest):
    """
    Process a user prompt and return an agent response.
    """
    try:
        response = await get_agent_response(data.user_id, data.user_prompt)
        return {"response": response}
    except Exception as e:
        print(f"Error processing prompt: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    

@router.post("/api/chat/message")
async def send_chat_message(request: dict):
    """Send a message to the AI coach and get a response"""
    try:
        user_id = request.get("user_id")
        message = request.get("message", "")
        
        print(f"📨 Chat message received for user_id: {user_id}")
        print(f"📝 Message: {message}")

        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id and message are required")
        
        # Get AI response using your existing agent
        response = await get_agent_response(user_id, message)
        
        return {
            "success": True,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Error in chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/chat/history/{user_id}")
async def get_chat_history(user_id: str):
    """Get chat history for a user"""
    try:
        print(f"📜 Getting chat history for user_id: {user_id}")
        from database import get_user_conversation
        conversation = await get_user_conversation(user_id)
        
        return {
            "success": True,
            "conversation": conversation
        }
        
    except Exception as e:
        print(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.put("/update-user/{user_id}")
async def update_user_profile(
    user_id: str,
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update user profile with field restrictions enforced.
    READONLY FIELDS: name, email, age, gender cannot be updated.
    """
    try:

        # DEBUG: Print exactly what we received
        print(f"🔍 Received user_data: {user_data}")
        print(f"🔍 Raw user_data dict: {user_data.dict()}")
        print(f"🔍 User_data dict exclude_none: {user_data.dict(exclude_none=True)}")

        # Get the user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get the update data, excluding None values
        update_data = user_data.dict(exclude_none=True)
        
        print(f"🔍 Received update data: {update_data}")
        
        # SECURITY CHECK: Ensure readonly fields are not being updated
        readonly_fields = {'name', 'email', 'age', 'gender', 'id', 'password_hash', 'created_at'}
        attempted_readonly_updates = set(update_data.keys()) & readonly_fields
        
        if attempted_readonly_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update readonly fields: {', '.join(attempted_readonly_updates)}. "
                       f"Fields 'name', 'email', 'age', and 'gender' cannot be modified."
            )
        
        # Store original values for health metric calculation
        original_height = user.height
        original_weight = user.weight
        original_age = user.age
        original_gender = user.gender
        original_activity = user.activity_level
        
        print(f"🔍 Original values: height={original_height}, weight={original_weight}, age={original_age}, gender={original_gender}, activity={original_activity}")
        
        # Update allowed fields
        for field, value in update_data.items():
            if hasattr(user, field) and field not in readonly_fields:
                # Convert string numbers to integers for specific fields
                if field in ['workout_frequency', 'workout_duration']:
                    if value is not None and value != '':
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Invalid value for {field}: must be a valid integer"
                            )
                
                # Convert string numbers to floats for specific fields
                elif field in ['height', 'weight', 'target_weight', 'sleep_hours', 'water_intake']:
                    if value is not None and value != '':
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Invalid value for {field}: must be a valid number"
                            )
                
                print(f"🔍 Setting {field} = {value}")
                setattr(user, field, value)
        
        # ALWAYS recalculate health metrics when physical stats OR activity level changes
        height_changed = 'height' in update_data
        weight_changed = 'weight' in update_data
        activity_changed = 'activity_level' in update_data
        
        print(f"🔍 Changes detected: height={height_changed}, weight={weight_changed}, activity={activity_changed}")
        
        # Force recalculation if any relevant field changed
        if height_changed or weight_changed or activity_changed:
            current_height = user.height or original_height
            current_weight = user.weight or original_weight
            current_age = original_age  # Age is readonly, so use original
            current_gender = original_gender  # Gender is readonly, so use original
            current_activity = user.activity_level or original_activity
            
            print(f"🔍 Current values for calculation: height={current_height}, weight={current_weight}, age={current_age}, gender={current_gender}, activity={current_activity}")
            
            if all([current_height, current_weight, current_age, current_gender, current_activity]):
                health_metrics = calculate_health_metrics(
                    current_height, current_weight, current_age, 
                    current_gender, current_activity
                )
                
                print(f"🔍 New health metrics: {health_metrics}")
                
                user.bmi = health_metrics['bmi']
                user.bmr = health_metrics['bmr']
                user.tdee = health_metrics['tdee']
            else:
                print(f"🔍 Missing required data for health calculation")
        
        # Update timestamp
        user.updated_at = datetime.now(timezone.utc)
        
        # Commit changes
        await db.commit()
        await db.refresh(user)
        
        # Return updated user data
        return {
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
            "tdee": user.tdee,
            "primary_goal": user.primary_goal,
            "fitness_goal": user.fitness_goal,
            "weight_goal": user.weight_goal,
            "target_weight": user.target_weight,
            "goal_timeline": user.goal_timeline,
            "sleep_hours": user.sleep_hours,
            "bedtime": user.bedtime,
            "wakeup_time": user.wakeup_time,
            "sleep_issues": user.sleep_issues,
            "dietary_preferences": user.dietary_preferences,
            "water_intake": user.water_intake,
            "medical_conditions": user.medical_conditions,
            "other_medical_condition": user.other_medical_condition,
            "preferred_workouts": user.preferred_workouts,
            "workout_frequency": user.workout_frequency,
            "workout_duration": user.workout_duration,
            "workout_location": user.workout_location,
            "available_equipment": user.available_equipment,
            "fitness_level": user.fitness_level,
            "has_trainer": user.has_trainer,
            "preferences": user.preferences,
            "updated_at": user.updated_at
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error updating user profile: {e}")
        traceback.print_exc()
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating profile"
        )
    

@router.put("/update-password/{user_id}")
async def update_user_password(user_id: str, password_data: dict):
    """Update user password with proper verification"""
    try:
        current_password = password_data.get("currentPassword")
        new_password = password_data.get("newPassword")
        
        if not current_password or not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both current and new passwords are required"
            )
        
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )
        
        print(f"🔐 Password update requested for user: {user_id}")
        
        # Get user from database using SQLAlchemy
        async with SessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # FIXED: Use dot notation instead of .get() for SQLAlchemy objects
            password_to_verify = user.password_hash or user.password
            
            if not password_to_verify:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No password set for user"
                )
            
            # Verify current password using the same system
            if not verify_password(current_password, password_to_verify):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Hash new password with passlib (same as login system)
            new_password_hash = get_password_hash(new_password)
            
            # Update both password fields for compatibility
            user.password = new_password_hash
            user.password_hash = new_password_hash
            user.updated_at = datetime.datetime.utcnow()
            
            await session.commit()
            
            print(f"✅ Password updated successfully for user: {user_id}")
            
            return {"message": "Password updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating password: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
@router.get("/user/{user_id}/editable-fields")
async def get_editable_fields(user_id: str, db: Session = Depends(get_db)):
    """
    Get list of fields that can be edited for a user.
    This endpoint helps the frontend know which fields to make readonly.
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get all user model fields
        all_fields = set(User.__table__.columns.keys())
        readonly_fields = User.READONLY_FIELDS
        editable_fields = all_fields - readonly_fields
        
        return {
            "editable_fields": list(editable_fields),
            "readonly_fields": list(readonly_fields),
            "restricted_message": "Fields 'name', 'email', 'age', and 'gender' cannot be modified from the profile page."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting editable fields: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/user/{user_id}/profile")
async def get_user_profile_route(user_id: str, db: Session = Depends(get_db)):
    """Get user profile with field editability information"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_dict = user.to_dict()
        
        # Add field restriction information
        user_dict['field_restrictions'] = {
            'readonly_fields': list(User.READONLY_FIELDS),
            'editable_fields': list(user.get_editable_fields()),
            'restriction_reason': {
                'name': 'Name cannot be changed for security reasons',
                'email': 'Email cannot be changed as it is used for login',
                'age': 'Age cannot be modified after account creation',
                'gender': 'Gender cannot be modified after account creation'
            }
        }
        
        return user_dict
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    
