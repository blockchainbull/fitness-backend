# flutter_models.py - Updated to work with unified backend
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import date

class HealthUserCreate(BaseModel):
    # Basic info
    name: str
    email: EmailStr
    password: str
    gender: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activityLevel: Optional[str] = None
    
    hasPeriods: Optional[bool] = None
    lastPeriodDate: Optional[str] = None
    cycleLength: Optional[int] = None
    cycleLengthRegular: Optional[bool] = None
    pregnancyStatus: Optional[str] = None
    periodTrackingPreference: Optional[str] = None
    
    # Health metrics
    bmi: Optional[float] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    
    # Goals
    primaryGoal: Optional[str] = ""
    weightGoal: Optional[str] = ""
    targetWeight: Optional[float] = 0
    goalTimeline: Optional[str] = ""
    
    # Sleep
    sleepHours: Optional[float] = 7
    bedtime: Optional[str] = ""
    wakeupTime: Optional[str] = ""
    sleepIssues: Optional[List[str]] = []
    
    # Diet
    dietaryPreferences: Optional[List[str]] = []
    waterIntake: Optional[float] = 2.0
    
    # Medical
    medicalConditions: Optional[List[str]] = []
    otherMedicalCondition: Optional[str] = ""
    
    # Exercise
    preferredWorkouts: Optional[List[str]] = []
    workoutFrequency: Optional[int] = 3
    workoutDuration: Optional[int] = 30
    workoutLocation: Optional[str] = ""
    availableEquipment: Optional[List[str]] = []
    fitnessLevel: Optional[str] = "Beginner"
    hasTrainer: Optional[bool] = False
    
    # Additional data (for compatibility)
    formData: Optional[dict] = None

class HealthUserResponse(BaseModel):
    success: bool
    userId: Optional[str] = None
    userProfile: Optional[dict] = None
    message: Optional[str] = None
    error: Optional[str] = None

class HealthLoginRequest(BaseModel):
    email: EmailStr
    password: str

class WaterIntakeRequest(BaseModel):
    date: date
    glasses: int

class MealRequest(BaseModel):
    date: date
    mealName: str
    description: str
    calories: int
    mealTime: str

class PeriodCycleData(BaseModel):
    hasPeriods: Optional[bool] = None
    lastPeriodDate: Optional[str] = None
    cycleLength: Optional[int] = None
    cycleLengthRegular: Optional[bool] = None
    pregnancyStatus: Optional[str] = None
    trackingPreference: Optional[str] = None

class UnifiedOnboardingRequest(BaseModel):
    basicInfo: Optional[Dict[str, Any]] = {}
    periodCycle: Optional[Dict[str, Any]] = {}
    primaryGoal: Optional[str] = ""
    weightGoal: Optional[Dict[str, Any]] = {}
    sleepInfo: Optional[Dict[str, Any]] = {}
    dietaryPreferences: Optional[Dict[str, Any]] = {}
    workoutPreferences: Optional[Dict[str, Any]] = {}
    exerciseSetup: Optional[Dict[str, Any]] = {}