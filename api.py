"""
API routes for the nutrition and exercise coach application.
"""
# api.py - Add this new endpoint for unified onboarding
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from database import create_user_from_onboarding, get_user_by_email, verify_password, get_user_profile
import traceback

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
async def submit_prompt(request: dict):
    """Submit a prompt to the AI agent"""
    try:
        user_prompt = request.get("user_prompt", "")
        agent_name = request.get("agent_name", "health_coach")
        user_id = request.get("user_id", "guest")
        
        # Process with your existing AI logic
        # This is a placeholder - replace with your actual AI processing
        response = f"AI response to: {user_prompt}"
        
        # Save conversation
        from database import append_to_user_conversation
        await append_to_user_conversation(user_id, user_prompt, response)
        
        return {"response": response}
        
    except Exception as e:
        print(f"Error processing prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))