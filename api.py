"""
API routes for the nutrition and exercise coach application.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import traceback
from database import get_user_conversation, get_user_profile, get_user_notes
from agent import get_agent_response
from models import PromptRequest, ConversationResponse
from pydantic import BaseModel
from database import SessionLocal, User 
from passlib.context import CryptContext
import secrets
import uuid
import datetime

# Create router
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

# Define the login request body
class LoginRequest(BaseModel):
    email: str
    password: str

class BasicInfo(BaseModel):
    name: str
    email: str
    password: str
    gender: str
    age: int
    height: float
    weight: float
    activityLevel: str
    bmi: float
    bmr: float
    tdee: float

class WeightGoal(BaseModel):
    weightGoal: str
    targetWeight: float
    timeline: str
    weightDifference: float

class SleepInfo(BaseModel):
    sleepHours: float
    bedtime: str
    wakeupTime: str
    sleepIssues: List[str]

class DietaryPreferences(BaseModel):
    dietaryPreferences: List[str]
    waterIntake: float
    medicalConditions: List[str]
    otherCondition: Optional[str] = None

class WorkoutPreferences(BaseModel):
    workoutTypes: List[str]
    frequency: int
    duration: int

class ExerciseSetup(BaseModel):
    workoutLocation: str
    equipment: List[str]
    fitnessLevel: str
    hasTrainer: bool

class OnboardingRequest(BaseModel):
    basicInfo: Optional[BasicInfo] = None
    primaryGoal: Optional[str] = None
    weightGoal: Optional[WeightGoal] = None
    sleepInfo: Optional[SleepInfo] = None
    dietaryPreferences: Optional[DietaryPreferences] = None
    workoutPreferences: Optional[WorkoutPreferences] = None
    exerciseSetup: Optional[ExerciseSetup] = None

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

@router.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login endpoint"""
    try:
        async with SessionLocal() as session:
            # Find user by email
            result = await session.execute(
                select(User).where(User.email == request.email)
            )
            user = result.scalars().first()
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            # Verify password
            if not verify_password(request.password, user.password):
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            # TODO: Generate JWT token here
            return {
                "success": True,
                "message": "Login successful",
                "user_id": str(user.id),
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/get-conversation/{user_id}", response_model=ConversationResponse)
async def get_conversation(user_id: str):
    """
    Retrieve the conversation history for a user.
    """
    try:
        print(f"User ID is {user_id}")
        messages = await get_user_conversation(user_id)
        print(f"Returning conversation with {len(messages)} messages")
        return {"conversation": messages}
    except Exception as e:
        print(f"Error in get_conversation endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")


@router.get("/test-agent/{user_id}")
async def test_agent(user_id: str):
    """
    Test endpoint to verify the agent functionality without full web integration.
    """
    try:
        test_prompt = "I want to lose weight."
        response = await get_agent_response(user_id, test_prompt)
        
        return {
            "status": "success",
            "user_id": user_id,
            "test_prompt": test_prompt,
            "response": response
        }
    except Exception as e:
        print(f"Error in test endpoint: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }
    

@router.get("/get-user-notes/{user_id}")
async def get_notes(user_id: str):
    """
    Retrieve structured notes for a user.
    """
    try:
        notes = await get_user_notes(user_id)
        return {
            "success": True,
            "notes": [
                {
                    "id": str(note.id),
                    "category": note.category,
                    "key": note.key,
                    "value": note.value,
                    "confidence": note.confidence,
                    "source": note.source,
                    "timestamp": note.timestamp.isoformat()
                }
                for note in notes
            ]
        }
    except Exception as e:
        print(f"Error retrieving user notes: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving user notes: {str(e)}")

@router.post("/api/onboarding/complete")
async def complete_onboarding(data: OnboardingRequest):
    """
    Complete the onboarding process and save user data.
    """
    try:
        print("Received onboarding data:")
        print(f"Basic Info: {data.basicInfo}")
        print(f"Primary Goal: {data.primaryGoal}")
        print(f"Weight Goal: {data.weightGoal}")
        print(f"Sleep Info: {data.sleepInfo}")
        print(f"Dietary Preferences: {data.dietaryPreferences}")
        print(f"Workout Preferences: {data.workoutPreferences}")
        print(f"Exercise Setup: {data.exerciseSetup}")
        
        # Check if we have basic info
        if not data.basicInfo or not data.basicInfo.password:
            raise HTTPException(status_code=400, detail="Password is required")
        
        hashed_password = hash_password(data.basicInfo.password)

        async with SessionLocal() as session:
            # Check if user with this email already exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == data.basicInfo.email)
            )
            existing_user = result.scalars().first()
            
            if existing_user:
                # Update existing user instead of creating new one
                print(f"User with email {data.basicInfo.email} already exists. Updating...")
                
                # Update existing user fields
                existing_user.name = data.basicInfo.name
                existing_user.gender = data.basicInfo.gender
                existing_user.age = data.basicInfo.age
                existing_user.height = data.basicInfo.height
                existing_user.weight = data.basicInfo.weight
                existing_user.activity_level = data.basicInfo.activityLevel
                existing_user.bmi = data.basicInfo.bmi
                existing_user.bmr = data.basicInfo.bmr
                existing_user.tdee = data.basicInfo.tdee
                existing_user.fitnessGoal = data.primaryGoal or "general_fitness"
                existing_user.dietaryPreferences = data.dietaryPreferences.dietaryPreferences if data.dietaryPreferences else []
                existing_user.updatedAt = datetime.datetime.utcnow()
                
                # Update preferences
                existing_user.preferences = {
                    "weightGoal": data.weightGoal.dict() if data.weightGoal else None,
                    "sleepInfo": data.sleepInfo.dict() if data.sleepInfo else None,
                    "workoutPreferences": data.workoutPreferences.dict() if data.workoutPreferences else None,
                    "exerciseSetup": data.exerciseSetup.dict() if data.exerciseSetup else None,
                    "dietaryPreferences": {
                        "waterIntake": data.dietaryPreferences.waterIntake if data.dietaryPreferences else None,
                        "medicalConditions": data.dietaryPreferences.medicalConditions if data.dietaryPreferences else [],
                        "otherCondition": data.dietaryPreferences.otherCondition if data.dietaryPreferences else None
                    } if data.dietaryPreferences else None
                }
                
                await session.commit()
                user_id = existing_user.id
                
            else:
                # Create new user
                user_id = uuid.uuid4()
                new_user = User(
                    id=user_id,
                    name=data.basicInfo.name,
                    email=data.basicInfo.email,
                    password=hashed_password,
                    
                    # Map basic info directly to fields
                    gender=data.basicInfo.gender,
                    age=data.basicInfo.age,
                    height=data.basicInfo.height,
                    weight=data.basicInfo.weight,
                    activity_level=data.basicInfo.activityLevel,
                    bmi=data.basicInfo.bmi,
                    bmr=data.basicInfo.bmr,
                    tdee=data.basicInfo.tdee,
                    
                    # Set fitness goal
                    fitnessGoal=data.primaryGoal or "general_fitness",
                    
                    # Set dietary preferences
                    dietaryPreferences=data.dietaryPreferences.dietaryPreferences if data.dietaryPreferences else [],
                    
                    # Store additional data in JSONB fields
                    preferences={
                        "weightGoal": data.weightGoal.dict() if data.weightGoal else None,
                        "sleepInfo": data.sleepInfo.dict() if data.sleepInfo else None,
                        "workoutPreferences": data.workoutPreferences.dict() if data.workoutPreferences else None,
                        "exerciseSetup": data.exerciseSetup.dict() if data.exerciseSetup else None,
                        "dietaryPreferences": {
                            "waterIntake": data.dietaryPreferences.waterIntake if data.dietaryPreferences else None,
                            "medicalConditions": data.dietaryPreferences.medicalConditions if data.dietaryPreferences else [],
                            "otherCondition": data.dietaryPreferences.otherCondition if data.dietaryPreferences else None
                        } if data.dietaryPreferences else None
                    },
                    
                    createdAt=datetime.datetime.utcnow(),
                    updatedAt=datetime.datetime.utcnow()
                )
                
                session.add(new_user)
                await session.commit()
            
            print(f"Successfully saved user with ID: {user_id}")
            
            return {
                "success": True,
                "message": "Onboarding completed successfully",
                "user_id": str(user_id)
            }
            
    except Exception as e:
        print(f"Error completing onboarding: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to complete onboarding: {str(e)}")



# @router.post("/auth/login")
# async def login(request: LoginRequest):
#     """
#     Simple login endpoint.
#     """
#     # Dummy login validation for now
#     if request.email == "testuser" and request.password == "testpass":
#         return {"status": "success", "message": "Login successful"}
#     else:
#         raise HTTPException(status_code=401, detail="Invalid username or password")

