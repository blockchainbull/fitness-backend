"""
Database models and functions for the nutrition and exercise coach API.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Index, select, update, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from contextlib import contextmanager
import uuid
import datetime
import traceback
import json

# SQLAlchemy setup
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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
    """Database model for users."""
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)

    gender = Column(String, nullable=True)  
    age = Column(Integer, nullable=True)    
    height = Column(Float, nullable=True)     
    weight = Column(Float, nullable=True)   
    activity_level = Column(String, nullable=True) 
    bmi = Column(Float, nullable=True)
    bmr = Column(Float, nullable=True)
    tdee = Column(Float, nullable=True)

    fitnessGoal = Column(String, nullable=True)
    dietaryPreferences = Column(ARRAY(String), nullable=True)
    healthMetrics = Column(JSONB, nullable=True)
    physicalStats = Column(JSONB, nullable=True)
    preferences = Column(JSONB, nullable=True)
    createdAt = Column(DateTime, default=datetime.datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.datetime.utcnow)
    version = Column(Integer, default=0)

class Conversation(Base):
    """Database model for storing user conversations."""
    __tablename__ = "Conversation"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    userId = Column(UUID(as_uuid=True), index=True)
    conversation = Column(MutableList.as_mutable(JSONB), nullable=False, default=list)


# New models for user notes
class UserNotes(Base):
    """Database model for storing structured user notes."""
    __tablename__ = "UserNotes"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    userId = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    category = Column(String, nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    confidence = Column(Float, default=0.5)
    source = Column(String, default="inferred")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('userId', 'key', name='userNotes_userId_key_unique'),
    )


async def get_user_conversation(user_id: str):
    """
    Retrieve the conversation history for a specific user.
    Creates a new conversation entry if none exists.
    """
    async with SessionLocal() as session:
        try:
            # First try to find existing conversation
            result = await session.execute(
                select(Conversation).where(Conversation.userId == user_id)
            )
            conversation_row = result.scalars().first()
            
            # If no conversation exists, create one
            if not conversation_row:
                print(f"No conversation found for user_id: {user_id}. Creating new conversation.")
                conversation_row = Conversation(
                    id=uuid.uuid4(),
                    userId=user_id,
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
    now = datetime.datetime.utcnow().isoformat()  # Format timestamp in ISO 8601 format

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
            # First, retrieve the current conversation record
            result = await session.execute(
                select(Conversation).where(Conversation.userId == user_id)
            )
            conversation_record = result.scalars().first()
            
            if not conversation_record:
                # Create a new record if user doesn't exist
                print(f"Creating new conversation record for user: {user_id}")
                # Initialize with an array containing both messages
                new_conversation = [user_message_entry, agent_message_entry]
                conversation_record = Conversation(
                    id=uuid.uuid4(),
                    userId=user_id,
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




# PRESERVED COMMENTED CODE: Alternative implementation (legacy)
# async def get_user_conversation(user_id: str):
    
#     async with SessionLocal() as session:
#         try:
#             result = await session.execute(
#                 select(Conversation.conversation).where(Conversation.userId == user_id)
#             )
#             conversation_data = result.scalar() or []

#             formatted_conversation = []
#             for entry in conversation_data:
#                 role = entry.get("role", "unknown")
#                 content = entry.get("content", "")
#                 timestamp = entry.get("timestamp", "")
#                 formatted_conversation.append({
#                     "role": role,
#                     "content": content,
#                     "timestamp": timestamp
#                 })
#             return formatted_conversation
#         except Exception as e:
#             print(f"🔥 Error fetching user conversation: {e}")
#             raise


# PRESERVED COMMENTED CODE: Alternative implementation (legacy)
# async def append_to_user_conversation(user_id: str, user_message: str, agent_message: str):
#     now = datetime.datetime.utcnow().isoformat()  # Format timestamp in ISO 8601 format

#     # Create new conversation entries for the user and assistant
#     user_message_entry = {
#         "role": "user",
#         "content": user_message,
#         "timestamp": now
#     }
    
#     agent_message_entry = {
#         "role": "assistant",
#         "content": agent_message,
#         "timestamp": now
#     }

#     async with SessionLocal() as session:
#         # First, retrieve the current conversation array
#         result = await session.execute(
#             select(Conversation.conversation)
#             .where(Conversation.userId == user_id)
#         )
#         conversation_data = result.scalar() or []

#         # Append the new user and assistant messages to the array
#         conversation_data.append(user_message_entry)
#         conversation_data.append(agent_message_entry)

#         # Update the conversation in the database
#         stmt = (
#             update(Conversation)
#             .where(Conversation.userId == user_id)
#             .values(conversation=conversation_data)
#         )
#         await session.execute(stmt)
#         await session.commit()


async def init_database():
    """
    Initialize the database tables and create default users if needed.
    Called during application startup.
    """
    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        

        # await migrate_user_table()

        # Only create default users - conversations will be created on-demand
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
                        new_user = User(
                            id=user_id_uuid,
                            name=name,
                            email=email or f"{user_id}@example.com",
                            password="hashed_password_here",  # Use proper hashing in production
                            fitnessGoal="generalFitness",
                            dietaryPreferences=[],
                            createdAt=datetime.datetime.utcnow(),
                            updatedAt=datetime.datetime.utcnow()
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


# Add functions to work with user notes
async def get_user_notes(user_id: str):
    """Retrieve all notes for a specific user."""
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(UserNotes).where(UserNotes.userId == user_id)
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
                .where(UserNotes.userId == user_id)
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
                        timestamp=datetime.datetime.utcnow()
                    )
                )
            else:
                # Create new note
                new_note = UserNotes(
                    id=uuid.uuid4(),
                    userId=user_id,
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

async def get_user_profile(user_id: str):
    """Get complete user profile including physical stats and preferences."""
    print(f"Fetching profile for user ID: {user_id}")
    
    # Convert string user_id to UUID using same logic as in init_database
    try:
        if isinstance(user_id, str) and len(user_id) < 32:
            # For short strings like "guest", use the same deterministic UUID generation
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
            
            # Debug output
            print(f"Raw physical stats from DB: {user.physicalStats}")
            print(f"Raw physical stats type: {type(user.physicalStats)}")
            
            # Ensure proper handling of physical stats
            physical_stats = {}
            if user.physicalStats:
                ps = user.physicalStats
                # Handle both dict and string formats
                if isinstance(ps, str):
                    try:
                        ps = json.loads(ps)
                    except:
                        ps = {}
                
                # Explicit conversion to ensure numeric values
                physical_stats = {
                    "height": float(ps.get("height", 0) or 0),
                    "weight": float(ps.get("weight", 0) or 0),
                    "age": int(ps.get("age", 0) or 0),
                    "gender": ps.get("gender", "male"),
                    "activityLevel": ps.get("activityLevel", "moderate")
                }
            
            # Similar handling for health metrics
            health_metrics = {}
            if user.healthMetrics:
                hm = user.healthMetrics
                if isinstance(hm, str):
                    try:
                        hm = json.loads(hm)
                    except:
                        hm = {}
                
                health_metrics = {
                    "bmr": float(hm.get("bmr", 0) or 0),
                    "tdee": float(hm.get("tdee", 0) or 0),
                    "bmi": float(hm.get("bmi", 0) or 0)
                }
            
            # Build the user data object with proper type conversions
            user_data = {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "fitnessGoal": user.fitnessGoal,
                "dietaryPreferences": user.dietaryPreferences or [],
                "healthMetrics": health_metrics,
                "physicalStats": physical_stats,
                "preferences": user.preferences or {}
            }
            
            print(f"Processed user data: {user_data}")
            return user_data
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            traceback.print_exc()
            return {}

# adding user onboarding related data 
async def migrate_user_table():
    """Add new columns to users table"""
    async with engine.begin() as conn:
        try:
            # Add new columns if they don't exist
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS gender VARCHAR,
                ADD COLUMN IF NOT EXISTS age INTEGER,
                ADD COLUMN IF NOT EXISTS height FLOAT,
                ADD COLUMN IF NOT EXISTS weight FLOAT,
                ADD COLUMN IF NOT EXISTS activity_level VARCHAR,
                ADD COLUMN IF NOT EXISTS bmi FLOAT,
                ADD COLUMN IF NOT EXISTS bmr FLOAT,
                ADD COLUMN IF NOT EXISTS tdee FLOAT;
            """))
            print("User table migration completed")
        except Exception as e:
            print(f"Migration error (might be normal if columns exist): {e}")