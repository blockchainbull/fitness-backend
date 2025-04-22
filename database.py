"""
Database models and functions for the nutrition and exercise coach API.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, select, update
from sqlalchemy.dialects.postgresql import JSONB
import datetime
import traceback
from config import DATABASE_URL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableList
import uuid

# SQLAlchemy setup
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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
    # try:
    #     # Create tables
    #     async with engine.begin() as conn:
    #         await conn.run_sync(Base.metadata.create_all)
        
    #     # Check if we need to initialize default conversation records
    #     async with SessionLocal() as session:
    #         # Helper function to add a test user if needed
    #         async def ensure_user_exists(user_id):
    #             result = await session.execute(
    #                 select(Conversation).where(Conversation.userId == user_id)
    #             )
    #             user = result.scalars().first()
                
    #             if not user:
    #                 print(f"Creating new conversation record for user: {user_id}")
    #                 new_user = Conversation(
    #                     userId=user_id,
    #                     conversation=[]  # Empty conversation array
    #                 )
    #                 session.add(new_user)
    #                 return True
    #             return False
            
    #         # Ensure some common user IDs exist
    #         changes = False
    #         changes |= await ensure_user_exists("guest")
    #         changes |= await ensure_user_exists("test-user")
            
    #         if changes:
    #             await session.commit()
                
    #     print("Database setup completed successfully")
    # except Exception as e:
    #     print(f"Error during database initialization: {e}")
    #     traceback.print_exc()