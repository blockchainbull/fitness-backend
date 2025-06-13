"""
API routes for the nutrition and exercise coach application.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from models import PromptRequest, ConversationResponse
from database import create_user_from_onboarding, get_user_by_email, verify_password, get_user_profile
from agent import get_agent_response
from passlib.context import CryptContext
from fastapi import HTTPException, status
import traceback
import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

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

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

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
            "timestamp": datetime.datetime.utcnow().isoformat()
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
async def update_user_profile(user_id: str, user_data: dict):
    """Update user profile information"""
    try:
        print(f"📝 Updating user profile for: {user_id}")
        print(f"📋 Update data: {user_data}")
        
        # Validate required fields if needed
        if 'email' in user_data:
            # Add email validation if needed
            pass
            
        # Calculate BMI if height and weight are provided
        height = user_data.get('height')
        weight = user_data.get('weight')
        
        if height and weight:
            height_m = height / 100  # Convert cm to meters
            bmi = weight / (height_m ** 2)
            user_data['bmi'] = round(bmi, 1)
            
            # Calculate BMR if age and gender are provided
            age = user_data.get('age')
            gender = user_data.get('gender')
            
            if age and gender:
                if gender.lower() == 'male':
                    bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
                else:
                    bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
                user_data['bmr'] = round(bmr)
                
                # Calculate TDEE based on activity level
                activity_multipliers = {
                    'sedentary': 1.2,
                    'lightlyActive': 1.375,
                    'moderatelyActive': 1.55,
                    'veryActive': 1.725,
                    'extraActive': 1.9
                }
                activity_level = user_data.get('activityLevel', 'moderatelyActive')
                tdee = bmr * activity_multipliers.get(activity_level, 1.55)
                user_data['tdee'] = round(tdee)
        
        # Update in database
        from database import update_user_in_db
        updated_user = await update_user_in_db(user_id, user_data)
        
        print(f"✅ User profile updated successfully")
        return updated_user
        
    except Exception as e:
        print(f"❌ Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

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
        
        # Get user from database
        from database import get_user_by_id, update_user_password_in_db
        user = await get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(current_password, user.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = get_password_hash(new_password)
        
        # Update password in database
        await update_user_password_in_db(user_id, new_password_hash)
        
        print(f"✅ Password updated successfully for user: {user_id}")
        
        return {"message": "Password updated successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"❌ Error updating password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )