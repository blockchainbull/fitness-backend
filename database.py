"""
Database models and functions for the nutrition and exercise coach API.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, select, update
from sqlalchemy.dialects.postgresql import JSONB
from config import DATABASE_URL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Index, select, update
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
import datetime
import traceback

# SQLAlchemy setup
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class User(Base):
    """Database model for users."""
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    fitnessGoal = Column(String, nullable=True)
    dietaryPreferences = Column(ARRAY(String), nullable=True)
    healthMetrics = Column(JSONB, nullable=True)
    createdAt = Column(DateTime, default=datetime.datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.datetime.utcnow)
    physicalStats = Column(JSONB, nullable=True)
    preferences = Column(JSONB, nullable=True)
    version = Column(Integer, default=0)

class Conversation(Base):
    """Database model for storing user conversations."""
    __tablename__ = "Conversation"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    userId = Column(UUID(as_uuid=True), index=True)
    conversation = Column(MutableList.as_mutable(JSONB), nullable=False, default=list)


async def get_user_conversation(user_id: str):
    """
    Retrieve the conversation history for a specific user.
    Creates a new conversation entry if none exists.
    """
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(Conversation).where(Conversation.userId == user_id)
            )
            conversation_row = result.scalars().first()
            
            if not conversation_row:
                print(f"No conversation found for user_id: {user_id}")
                return []  # No new conversation will be created, just return an empty list
            
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
        
        # Check if we need to initialize default conversation records
        async with SessionLocal() as session:
            # Helper function to add a test user if needed
            async def ensure_user_exists(user_id):
                # Handle non-UUID strings by generating a deterministic UUID
                try:
                    if isinstance(user_id, str) and len(user_id) < 32:
                        # This creates a deterministic UUID for the same string
                        user_id_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))
                        print(f"Converting '{user_id}' to UUID: {user_id_uuid}")
                    else:
                        # If it's already a valid UUID string or object, keep it
                        user_id_uuid = user_id
                except Exception as e:
                    print(f"Error converting user_id to UUID: {e}")
                    user_id_uuid = str(uuid.uuid4())  # Generate random UUID as fallback
                
                result = await session.execute(
                    select(Conversation).where(Conversation.userId == user_id_uuid)
                )
                user = result.scalars().first()
                
                if not user:
                    print(f"Creating new conversation record for user: {user_id_uuid}")
                    new_user = Conversation(
                        id=uuid.uuid4(),
                        userId=user_id_uuid,
                        conversation=[]  # Empty conversation array
                    )
                    session.add(new_user)
                    return True
                return False
            
            # Ensure some common user IDs exist - now with UUID conversion
            changes = False
            changes |= await ensure_user_exists("guest")
            changes |= await ensure_user_exists("test-user")
            
            if changes:
                await session.commit()
                
        print("Database setup completed successfully")
    except Exception as e:
        print(f"Error during database initialization: {e}")
        traceback.print_exc()



# New models for user notes
class UserNotes(Base):
    """Database model for storing structured user notes."""
    __tablename__ = "UserNotes"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    userId = Column(UUID(as_uuid=True), ForeignKey("User.id"), index=True)
    category = Column(String, nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    confidence = Column(Float, default=0.5)
    source = Column(String, default="inferred")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('userId', 'key', name='userNotes_userId_key_unique'),
    )

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
                
            # Make sure healthMetrics is properly handled as a dict, not a list
            user_data = {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "fitnessGoal": user.fitnessGoal,
                "dietaryPreferences": user.dietaryPreferences or [],
                "healthMetrics": user.healthMetrics or {}, # Change from [] to {}
                "physicalStats": user.physicalStats or {},
                "preferences": user.preferences or {}
            }
            print(f"Retrieved user data: {user_data}")
            return user_data
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            traceback.print_exc()
            return {}
        

