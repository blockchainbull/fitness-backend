"""
Updated unified database models for both web and Flutter applications.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, select, update, Boolean, TIMESTAMP, UUID
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from passlib.context import CryptContext
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone, timedelta
import os
import psycopg2
import uuid
import traceback


# SQLAlchemy setup
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@contextmanager
def get_health_db_cursor():
    """Database cursor specifically for health data"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'health_ai_db'),
        user=os.getenv('DB_USERNAME', 'health_ai_user'),
        password=os.getenv('DB_PASSWORD', 'health_ai_password')
    )
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

class User(Base):
    """Unified database model for users - supports both web and Flutter apps."""
    __tablename__ = "users"
    
    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # RESTRICTED FIELDS - These cannot be edited from profile page
    name = Column(String(255), nullable=False)  # READONLY
    email = Column(String(255), unique=True, nullable=False)  # READONLY
    age = Column(Integer, nullable=True)  # READONLY
    gender = Column(String(50), nullable=True)  # READONLY

    password = Column(String(255), nullable=False)  # For Flutter
    password_hash = Column(String(255), nullable=True)  # For web (can be same as password)
    
    height = Column(Float, nullable=True)  # in cm
    weight = Column(Float, nullable=True)  # in kg
    starting_weight = Column(Float)
    starting_weight_date = Column(TIMESTAMP(timezone=True))
    activity_level = Column(String(100), nullable=True)
    
    # Calculated health metrics
    bmi = Column(Float, nullable=True)
    bmr = Column(Float, nullable=True)
    tdee = Column(Float, nullable=True)
    
    # Reproductive health fields
    has_periods = Column(Boolean, nullable=True)
    last_period_date = Column(DateTime, nullable=True)
    cycle_length = Column(Integer, nullable=True)
    cycle_length_regular = Column(Boolean, nullable=True)
    pregnancy_status = Column(String(50), nullable=True)
    period_tracking_preference = Column(String(50), nullable=True)

    # Goals and preferences
    primary_goal = Column(String(100), nullable=True)
    fitness_goal = Column(String(100), nullable=True)  # Web frontend compatibility
    weight_goal = Column(String(50), nullable=True)
    target_weight = Column(Float, nullable=True)
    goal_timeline = Column(String(50), nullable=True)
    
    # Sleep information
    sleep_hours = Column(Float, nullable=True, default=7.0)
    bedtime = Column(String(10), nullable=True)  # e.g., "22:30"
    wakeup_time = Column(String(10), nullable=True)  # e.g., "06:30"
    sleep_issues = Column(ARRAY(String), nullable=True)
    
    # Nutrition and health
    dietary_preferences = Column(ARRAY(String), nullable=True)
    water_intake = Column(Float, nullable=True, default=2.0)
    medical_conditions = Column(ARRAY(String), nullable=True)
    other_medical_condition = Column(String, nullable=True)
    
    # Exercise preferences
    preferred_workouts = Column(ARRAY(String), nullable=True)
    workout_frequency = Column(Integer, nullable=True, default=3)
    workout_duration = Column(Integer, nullable=True, default=30)
    workout_location = Column(String(100), nullable=True)
    available_equipment = Column(ARRAY(String), nullable=True)
    fitness_level = Column(String(50), nullable=True, default='Beginner')
    has_trainer = Column(Boolean, nullable=True, default=False)
    
    # Web frontend specific fields (for backward compatibility)
    health_metrics = Column(JSONB, nullable=True)
    physical_stats = Column(JSONB, nullable=True)
    preferences = Column(JSONB, nullable=True)
    
    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    version = Column(Integer, default=0)
    
    # Additional timestamps for web frontend compatibility
    createdAt = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Define which fields are readonly (cannot be updated via profile)
    READONLY_FIELDS = {'name', 'email', 'age', 'gender', 'password_hash', 'id', 'created_at'}
    
    def get_editable_fields(self):
        """Return list of fields that can be edited from profile page"""
        all_fields = set(self.__table__.columns.keys())
        return all_fields - self.READONLY_FIELDS

class DailySteps(Base):
    """Daily step tracking"""
    __tablename__ = "daily_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    steps = Column(Integer, default=0)
    calories_burned = Column(Float, default=0.0)
    distance_km = Column(Float, default=0.0)
    active_minutes = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))  

class DailyNutrition(Base):
    """Daily nutrition tracking"""
    __tablename__ = "daily_nutrition"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    calories_consumed = Column(Float, default=0.0)
    protein_g = Column(Float, default=0.0)
    carbs_g = Column(Float, default=0.0)
    fat_g = Column(Float, default=0.0)
    water_liters = Column(Float, default=0.0)
    meals_logged = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)) 

class DailySleep(Base):
    """Daily sleep tracking"""
    __tablename__ = "daily_sleep"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    bedtime = Column(DateTime)
    wake_time = Column(DateTime)
    total_hours = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)
    deep_sleep_hours = Column(Float, default=0.0)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

class DailyWeight(Base):
    """Daily weight tracking"""
    __tablename__ = "daily_weight"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(TIMESTAMP(timezone=True), nullable=False)
    weight_kg = Column(Float, nullable=False)
    body_fat_percentage = Column(Float)
    muscle_mass_kg = Column(Float)
    notes = Column(String(500))
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

class WorkoutSessions(Base):
    """Workout session tracking"""
    __tablename__ = "workout_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    workout_type = Column(String(100))
    duration_minutes = Column(Integer)
    calories_burned = Column(Float)
    intensity = Column(String(20))
    notes = Column(String(1000))
    exercises = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

class PeriodTracking(Base):
    """Period tracking for female users"""
    __tablename__ = "period_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    flow_intensity = Column(String(20))
    symptoms = Column(ARRAY(String))
    mood = Column(String(20))
    notes = Column(String(500))
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))  

class SupplementTracking(Base):
    """Daily supplement tracking"""
    __tablename__ = "supplement_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    supplement_name = Column(String(100), nullable=False)
    dosage = Column(String(50))
    taken = Column(Boolean, default=False)
    time_taken = Column(DateTime)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)) 

class Conversation(Base):
    """Database model for storing user conversations."""
    __tablename__ = "conversations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), index=True)
    conversation = Column(MutableList.as_mutable(JSONB), nullable=False, default=list)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))  
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)) 

class UserNotes(Base):
    """Database model for storing structured user notes."""
    __tablename__ = "user_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    category = Column(String(100), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(String, nullable=False)
    confidence = Column(Float, default=0.5)
    source = Column(String(50), default="inferred")
    timestamp = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        UniqueConstraint('user_id', 'key', name='user_notes_user_id_key_unique'),
    )

# Password hashing utilities
def hash_password(password: str) -> str:
    """Hash a password for storing in database"""
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(password, hashed_password)

def parse_date_string(date_str):
    """Parse date string in ISO format"""
    if not date_str:
        return None
    
    try:
        # Parse ISO format date (e.g., "2024-01-15")
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))  # FIXED
    except (ValueError, AttributeError):
        return None

def parse_time_string(time_str):
    """Parse time string in either 12-hour or 24-hour format"""
    if not time_str:
        return ''
    
    # Handle 12-hour format (e.g., "10:00 PM")
    if 'AM' in time_str.upper() or 'PM' in time_str.upper():
        try:
            # Parse 12-hour format
            time_obj = datetime.strptime(time_str, '%I:%M %p')  # FIXED
            # Convert to 24-hour format for database
            return time_obj.strftime('%H:%M')
        except ValueError:
            pass
    
    # Handle 24-hour format (e.g., "22:00")
    try:
        # Validate 24-hour format
        datetime.strptime(time_str, '%H:%M')  # FIXED
        return time_str
    except ValueError:
        pass
    
    # Return empty string if parsing fails
    return ''

# Updated user creation function for onboarding
async def create_user_from_onboarding(onboarding_data: dict) -> str:
    """Create a new user from onboarding data (works for both web and Flutter)"""
    async with SessionLocal() as session:
        try:
            print("🔍 DEBUGGING USER CREATION:")
            print(f"📧 Email: {onboarding_data.get('basicInfo', {}).get('email')}")
            
            # Extract basic info
            basic_info = onboarding_data.get('basicInfo', {})

            raw_password = basic_info.get('password','defaultpassword123')

            if not raw_password or raw_password.strip() == '':
                raw_password = 'defaultpassword123'
            
            print(f"🔐 DEBUGGING PASSWORD CREATION:")
            print(f"  Raw password received: '{raw_password}'")
            print(f"  Password length: {len(raw_password)}")

            hashed_password = hash_password(raw_password)

            print(f"  Hashed password length: {len(hashed_password)}")
            print(f"  Hashed password starts with: {hashed_password[:10]}...")

            period_cycle = onboarding_data.get('periodCycle', {})
            
            # ADD THIS DEBUGGING
            print(f"🌸 Period cycle data in create_user_from_onboarding:")
            print(f"  period_cycle dict: {period_cycle}")
            print(f"  hasPeriods: {period_cycle.get('hasPeriods')}")
            print(f"  lastPeriodDate: {period_cycle.get('lastPeriodDate')}")
            print(f"  cycleLength: {period_cycle.get('cycleLength')}")

            primary_goal = onboarding_data.get('primaryGoal', '')
            weight_goal_data = onboarding_data.get('weightGoal', {})
            sleep_info = onboarding_data.get('sleepInfo', {})
            dietary_prefs = onboarding_data.get('dietaryPreferences', {})
            workout_prefs = onboarding_data.get('workoutPreferences', {})
            exercise_setup = onboarding_data.get('exerciseSetup', {})

            bedtime_raw = sleep_info.get('bedtime', '')
            wakeup_time_raw = sleep_info.get('wakeupTime', '')
            
            bedtime_parsed = parse_time_string(bedtime_raw)
            wakeup_time_parsed = parse_time_string(wakeup_time_raw)
            
            print(f"🕐 Time parsing:")
            print(f"  Raw bedtime: '{bedtime_raw}' -> Parsed: '{bedtime_parsed}'")
            print(f"  Raw wakeup: '{wakeup_time_raw}' -> Parsed: '{wakeup_time_parsed}'")
            

            has_periods = None
            last_period_date = None
            cycle_length = None
            cycle_length_regular = None
            pregnancy_status = None
            period_tracking_preference = None
            
            if period_cycle:
                has_periods = period_cycle.get('hasPeriods')
                last_period_date_str = period_cycle.get('lastPeriodDate')
                cycle_length = period_cycle.get('cycleLength')
                cycle_length_regular = period_cycle.get('cycleLengthRegular')
                pregnancy_status = period_cycle.get('pregnancyStatus')
                period_tracking_preference = period_cycle.get('trackingPreference')
                
                # Parse last period date if provided
                if last_period_date_str:
                    try:
                        last_period_date = datetime.fromisoformat(last_period_date_str.replace('Z', '+00:00'))
                        print(f"✅ Parsed last period date: {last_period_date}")
                    except:
                        print(f"❌ Failed to parse last period date: {last_period_date_str}")
                        last_period_date = None
                
                print(f"🌸 Processed period data:")
                print(f"  has_periods: {has_periods}")
                print(f"  last_period_date: {last_period_date}")
                print(f"  cycle_length: {cycle_length}")
                print(f"  cycle_length_regular: {cycle_length_regular}")
                print(f"  pregnancy_status: {pregnancy_status}")
                print(f"  period_tracking_preference: {period_tracking_preference}")


            # Create new user with SNAKE_CASE field names (matching your User model)
            new_user = User(
                id=uuid.uuid4(),
                name=basic_info.get('name', ''),
                email=basic_info.get('email', ''),
                password=hashed_password,
                password_hash=hashed_password,  
                
                # Physical characteristics
                gender=basic_info.get('gender', ''),
                age=basic_info.get('age', 0),
                height=basic_info.get('height', 0.0),
                weight=basic_info.get('weight', 0.0),
                starting_weight=basic_info.get('weight', 0.0),
                starting_weight_date=datetime.now(timezone.utc),
                activity_level=basic_info.get('activityLevel', ''),  
                
                # Health metrics
                bmi=basic_info.get('bmi', 0.0),
                bmr=basic_info.get('bmr', 0.0),
                tdee=basic_info.get('tdee', 0.0),
                
                # Period Cycle
                has_periods=period_cycle.get('hasPeriods', None),
                last_period_date=parse_date_string(period_cycle.get('lastPeriodDate', '')),
                cycle_length=period_cycle.get('cycleLength', None),
                cycle_length_regular=period_cycle.get('cycleLengthRegular', None),
                pregnancy_status=period_cycle.get('pregnancyStatus', None),
                period_tracking_preference=period_cycle.get('trackingPreference', None),

                # Goals
                primary_goal=primary_goal,
                fitness_goal=primary_goal,  
                weight_goal=weight_goal_data.get('weightGoal', ''),  
                target_weight=weight_goal_data.get('targetWeight', 0.0),  
                goal_timeline=weight_goal_data.get('timeline', ''),  
                
                # Sleep
                sleep_hours=sleep_info.get('sleepHours', 8.0),  
                bedtime=bedtime_parsed,
                wakeup_time=wakeup_time_parsed,
                sleep_issues=sleep_info.get('sleepIssues', []),  
                
                # Nutrition
                dietary_preferences=dietary_prefs.get('dietaryPreferences', []),  
                water_intake=dietary_prefs.get('waterIntake', 2.0),  
                medical_conditions=dietary_prefs.get('medicalConditions', []),  
                other_medical_condition=dietary_prefs.get('otherCondition', ''), 
                
                # Exercise
                preferred_workouts=workout_prefs.get('workoutTypes', []), 
                workout_frequency=workout_prefs.get('frequency', 3),
                workout_duration=workout_prefs.get('duration', 30),
                workout_location=exercise_setup.get('workoutLocation', ''), 
                available_equipment=exercise_setup.get('equipment', []), 
                fitness_level=exercise_setup.get('fitnessLevel', 'Beginner'), 
                has_trainer=exercise_setup.get('hasTrainer', False), 
                
                # Web frontend compatibility
                health_metrics={
                    'bmi': basic_info.get('bmi', 0.0),
                    'bmr': basic_info.get('bmr', 0.0),
                    'tdee': basic_info.get('tdee', 0.0)
                },
                physical_stats={
                    'height': basic_info.get('height', 0.0),
                    'weight': basic_info.get('weight', 0.0),
                    'age': basic_info.get('age', 0),
                    'gender': basic_info.get('gender', ''),
                    'activityLevel': basic_info.get('activityLevel', '')
                }
            )

            test_verify = verify_password(raw_password, hashed_password)

            print(f"👤 Created user object with period data:")
            print(f"  user.has_periods: {new_user.has_periods}")
            print(f"  user.last_period_date: {new_user.last_period_date}")
            print(f"  user.cycle_length: {new_user.cycle_length}")

            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            print(f"✅ User created successfully with ID: {new_user.id}")
            return str(new_user.id)
            
        except Exception as e:
            await session.rollback()
            print(f"Error creating user: {e}")
            traceback.print_exc()
            raise

async def get_user_by_email(email: str):
    """Get user by email for login"""
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalars().first()
        except Exception as e:
            print(f"Error fetching user by email: {e}")
            return None

async def get_user_by_id(user_id: str):
    """Get user by ID"""
    async with SessionLocal() as session:
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalars().first()
        except Exception as e:
            print(f"Error fetching user by ID: {e}")
            return None

async def get_user_conversation(user_id: str):
    """
    Retrieve the conversation history for a specific user.
    Creates a new conversation entry if none exists.
    """
    async with SessionLocal() as session:
        try:
            # Convert string to UUID if needed
            if isinstance(user_id, str):
                try:
                    user_id_uuid = uuid.UUID(user_id)
                except ValueError:
                    # If it's not a valid UUID, try to find user by email first
                    user = await get_user_by_email(user_id)
                    if user:
                        user_id_uuid = user.id
                    else:
                        # Create deterministic UUID for guest users
                        user_id_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
            else:
                user_id_uuid = user_id
            
            print(f"🔍 Looking for conversation with UUID: {user_id_uuid}")

            # First try to find existing conversation
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation_row = result.scalars().first()
            
            # If no conversation exists, create one
            if not conversation_row:
                print(f"No conversation found for user_id: {user_id}. Creating new conversation.")
                conversation_row = Conversation(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    conversation=[]  # Empty conversation array
                )
                session.add(conversation_row)
                await session.commit()
                return []  # Return empty conversation
            
            conversation_data = conversation_row.conversation if conversation_row else []
            print(f"Raw conversation data: {conversation_data}")
            
            # Make sure we're working with an array
            if not isinstance(conversation_data, list):
                print(f"Warning: conversation_data is not a list. Type: {type(conversation_data)}")
                conversation_data = []
            
            return conversation_data
        except Exception as e:
            print(f"🔥 Error fetching user conversation: {e}")
            traceback.print_exc()
            return []

async def append_to_user_conversation(user_id: str, user_message: str, agent_message: str):
    """
    Add new user and agent messages to the conversation history.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Create new conversation entries for the user and assistant
    user_message_entry = {
        "role": "user",
        "content": user_message,
        "timestamp": now
    }
    
    agent_message_entry = {
        "role": "assistant",
        "content": agent_message,
        "timestamp": now
    }

    try:
        async with SessionLocal() as session:

             # Convert string to UUID if needed
            if isinstance(user_id, str):
                try:
                    user_id_uuid = uuid.UUID(user_id)
                except ValueError:
                    # If it's not a valid UUID, try to find user by email first
                    user = await get_user_by_email(user_id)
                    if user:
                        user_id_uuid = user.id
                    else:
                        # Create deterministic UUID for guest users
                        user_id_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
            else:
                user_id_uuid = user_id
            
            print(f"💾 Saving conversation for UUID: {user_id_uuid}")


            # First, retrieve the current conversation record
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation_record = result.scalars().first()
            
            if not conversation_record:
                # Create a new record if user doesn't exist
                print(f"Creating new conversation record for user: {user_id}")
                # Initialize with an array containing both messages
                new_conversation = [user_message_entry, agent_message_entry]
                conversation_record = Conversation(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    conversation=new_conversation
                )
                session.add(conversation_record)
            else:
                print(f"Updating existing conversation for user: {user_id}")
                
                if conversation_record.conversation is None:
                    conversation_record.conversation = []
                    
                print(conversation_record.conversation)

                if not isinstance(conversation_record.conversation, list):
                    print(f"WARNING: conversation is not a list: {type(conversation_record.conversation)}")
                    conversation_record.conversation = []

                conversation_record.conversation.append(user_message_entry)
                conversation_record.conversation.append(agent_message_entry)

            await session.commit()
            print(f"Successfully appended messages for user: {user_id}")
            
    except Exception as e:
        print(f"Error appending to conversation: {e}")
        traceback.print_exc()
        raise

async def get_user_profile(user_id: str):
    """Get complete user profile including physical stats and preferences."""
    print(f"Fetching profile for user ID: {user_id}")
    
    # Convert string user_id to UUID
    try:
        if isinstance(user_id, str) and len(user_id) < 32:
            # For short strings like "guest", use deterministic UUID generation
            user_id_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
            print(f"Converting '{user_id}' to UUID: {user_id_uuid}")
        elif isinstance(user_id, str):
            # For strings that might already be UUIDs
            user_id_uuid = uuid.UUID(user_id)
        else:
            # If it's already a UUID object
            user_id_uuid = user_id
    except ValueError:
        # Handle invalid UUID format
        print(f"Invalid UUID format for user_id: {user_id}")
        return {}
    
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.id == user_id_uuid)
            )
            user = result.scalars().first()
            
            if not user:
                print(f"No user found with ID: {user_id} (UUID: {user_id_uuid})")
                return {}
            
            # Build comprehensive user data object
            user_data = {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                
                # Physical stats
                "gender": user.gender,
                "age": user.age,
                "height": user.height,
                "weight": user.weight,
                "activityLevel": user.activity_level,
                
                # Health metrics
                "bmi": user.bmi,
                "bmr": user.bmr,
                "tdee": user.tdee,
                
                # Reproductive health fields
                "hasPeriods": user.has_periods,
                "has_periods": user.has_periods,
                "lastPeriodDate": user.last_period_date,  
                "last_period_date": user.last_period_date,
                "cycleLength": user.cycle_length,
                "cycle_length": user.cycle_length,
                "cycleLengthRegular": user.cycle_length_regular,
                "cycle_length_regular": user.cycle_length_regular,
                "pregnancyStatus": user.pregnancy_status,
                "pregnancy_status": user.pregnancy_status,
                "periodTrackingPreference": user.period_tracking_preference,
                "period_tracking_preference": user.period_tracking_preference,

                # Goals
                "primaryGoal": user.primary_goal,
                "fitnessGoal": user.fitness_goal or user.primary_goal,
                "weightGoal": user.weight_goal,
                "targetWeight": user.target_weight,
                "goalTimeline": user.goal_timeline,
                
                # Sleep
                "sleepHours": user.sleep_hours,
                "bedtime": user.bedtime,
                "wakeupTime": user.wakeup_time,
                "sleepIssues": user.sleep_issues or [],
                
                # Nutrition
                "dietaryPreferences": user.dietary_preferences or [],
                "waterIntake": user.water_intake,
                "medicalConditions": user.medical_conditions or [],
                "otherMedicalCondition": user.other_medical_condition,
                
                # Exercise
                "preferredWorkouts": user.preferred_workouts or [],
                "workoutFrequency": user.workout_frequency,
                "workoutDuration": user.workout_duration,
                "workoutLocation": user.workout_location,
                "availableEquipment": user.available_equipment or [],
                "fitnessLevel": user.fitness_level,
                "hasTrainer": user.has_trainer,
                
                # Web frontend compatibility
                "healthMetrics": {
                    "bmr": float(user.bmr or 0),
                    "tdee": float(user.tdee or 0),
                    "bmi": float(user.bmi or 0)
                },
                "physicalStats": {
                    "height": float(user.height or 0),
                    "weight": float(user.weight or 0),
                    "age": int(user.age or 0),
                    "gender": user.gender or "male",
                    "activityLevel": user.activity_level or "moderate"
                },
                "preferences": user.preferences or {}
            }
            
            print(f"Processed user data: {user_data}")
            return user_data
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            traceback.print_exc()
            return {}

async def init_database():
    """
    Initialize the database tables and create default users if needed.
    Called during application startup.
    """
    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create default users
        async with SessionLocal() as session:
            # Helper function to ensure a user exists
            async def ensure_user_exists(user_id, name, email=None):
                try:
                    if isinstance(user_id, str) and len(user_id) < 32:
                        # Create deterministic UUID
                        user_id_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))
                    else:
                        user_id_uuid = user_id
                        
                    # Check if user exists
                    result = await session.execute(
                        select(User).where(User.id == user_id_uuid)
                    )
                    user = result.scalars().first()
                    
                    if not user:
                        # Create default user
                        hashed_password = hash_password("defaultpassword123")
                        new_user = User(
                            id=user_id_uuid,
                            name=name,
                            email=email or f"{user_id}@example.com",
                            password=hashed_password,
                            password_hash=hashed_password,
                            fitness_goal="generalFitness",
                            primary_goal="generalFitness",
                            dietary_preferences=[],
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc)
                        )
                        session.add(new_user)
                        await session.flush()
                        print(f"Created default user: {name} with ID {user_id_uuid}")
                        return True
                    return False
                except Exception as e:
                    print(f"Error creating user: {e}")
                    return False
            
            # Create default users
            changes = False
            changes |= await ensure_user_exists("guest", "Guest User")
            changes |= await ensure_user_exists("test-user", "Test User")
            
            if changes:
                await session.commit()
                
        print("Database setup completed successfully")
    except Exception as e:
        print(f"Error during database initialization: {e}")
        traceback.print_exc()

# Keep existing user notes functions unchanged...
async def get_user_notes(user_id: str):
    """Retrieve all notes for a specific user."""
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(UserNotes).where(UserNotes.user_id == user_id)
                .order_by(UserNotes.confidence.desc())
            )
            notes = result.scalars().all()
            return notes
        except Exception as e:
            print(f"Error fetching user notes: {e}")
            traceback.print_exc()
            return []

async def add_or_update_user_note(
    user_id: str, 
    category: str, 
    key: str, 
    value: str, 
    confidence: float = 0.5,
    source: str = "inferred"
):
    """Add or update a user note."""
    async with SessionLocal() as session:
        try:
            # Check if note exists
            result = await session.execute(
                select(UserNotes)
                .where(UserNotes.user_id == user_id)
                .where(UserNotes.key == key)
            )
            note = result.scalars().first()
            
            if note:
                # Update existing note
                await session.execute(
                    update(UserNotes)
                    .where(UserNotes.id == note.id)
                    .values(
                        value=value,
                        confidence=confidence,
                        source=source,
                        category=category,
                        timestamp=datetime.now(timezone.utc)
                    )
                )
            else:
                # Create new note
                new_note = UserNotes(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    category=category,
                    key=key,
                    value=value,
                    confidence=confidence,
                    source=source
                )
                session.add(new_note)
                
            await session.commit()
            return True
        except Exception as e:
            print(f"Error adding/updating user note: {e}")
            traceback.print_exc()
            return False
        

async def update_user_in_db(user_id: str, update_data: dict):
    """Update user information in database"""
    try:
        # Calculate BMI if height and weight are provided
        height = update_data.get('height')
        weight = update_data.get('weight')
        
        if height and weight:
            height_m = height / 100  # Convert cm to meters
            bmi = weight / (height_m ** 2)
            update_data['bmi'] = round(bmi, 1)
            
            # Calculate BMR if age and gender are provided
            age = update_data.get('age')
            gender = update_data.get('gender')
            
            if age and gender:
                if gender.lower() == 'male':
                    bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
                else:
                    bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
                update_data['bmr'] = round(bmr)
        
                # Update in your database (adjust based on your database setup)
                # This is a placeholder - implement based on your database
                users_collection = get_database()["users"]

                result = await users_collection.update_one(
                {"id": user_id},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise Exception(f"User with id {user_id} not found")
            
            # Get updated user
            updated_user = await users_collection.find_one({"id": user_id})
            if updated_user:
                updated_user.pop('_id', None)  # Remove MongoDB _id field
                return updated_user
            else:
                raise Exception("Failed to retrieve updated user")
           
    except Exception as e:
        print(f"Database error updating user: {e}")
        raise e
    
async def update_user_password_in_db(user_id: str, new_password_hash: str):
    """Update user password in database"""
    try:
        users_collection = get_database()["users"]
        
        result = await users_collection.update_one(
            {"id": user_id},
            {"$set": {"password_hash": new_password_hash}}
        )
        
        if result.matched_count == 0:
            raise Exception(f"User with id {user_id} not found")
        
        print(f"✅ Password hash updated in database for user: {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ Database error updating password: {e}")
        raise e
