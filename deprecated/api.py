from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, select, update
from sqlalchemy.dialects.postgresql import JSONB  # Correct import for JSONB
import datetime
import os
import asyncio
import traceback
import re
from any_agent import AgentConfig, AnyAgent  # Updated import for any-agent
from any_agent.tools import search_web, visit_webpage  # Example tools to use
from any_agent.tracing import setup_tracing  # Optional, but recommended for tracing
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from markupsafe import escape
# Load environment variables
load_dotenv()

# Database and API config
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

# SQLAlchemy setup
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# openAI client
client_openai = OpenAI()

class Conversation(Base):
    __tablename__ = "Conversation"
    id = Column(Integer, primary_key=True, index=True)
    userId = Column(String, index=True)
    conversation = Column(JSONB)  # This will store an array of JSONB objects

# HTML formatter
def format_response_as_html(text: str) -> str:
    lines = text.strip().splitlines()
    html = []
    in_ul = False
    in_ol = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("**") and stripped.endswith("**"):
            stripped = stripped[2:-2].strip()

        if stripped.startswith("### "):
            html.append(f"<h3>{escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            html.append(f"<h2>{escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            html.append(f"<h1>{escape(stripped[2:])}</h1>")

        elif stripped.startswith("- "):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{escape(stripped[2:])}</li>")

        elif re.match(r"^\d+\.\s", stripped):
            if not in_ol:
                html.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s", "", stripped)
            html.append(f"<li>{escape(item)}</li>")

        elif ":" in stripped and not stripped.startswith("http"):
            key, value = stripped.split(":", 1)
            html.append(f"<p><strong>{escape(key.strip())}:</strong> {escape(value.strip())}</p>")

        elif not stripped:
            if in_ul:
                html.append("</ul>")
                in_ul = False
            if in_ol:
                html.append("</ol>")
                in_ol = False
            html.append("<br>")

        else:
            html.append(f"<p>{escape(stripped)}</p>")

    if in_ul:
        html.append("</ul>")
    if in_ol:
        html.append("</ol>")

    return "\n".join(html)

# FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request & Response Models
class PromptRequest(BaseModel):
    user_id: str
    user_prompt: str
    agent_name: str

# DB functions
async def get_user_conversation(user_id: str):
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(Conversation).where(Conversation.userId == user_id)
            )
            conversation_row = result.scalars().first()
            
            if not conversation_row:
                print(f"No conversation found for user_id: {user_id}")
                # Initialize an empty conversation entry for this user
                new_conversation = Conversation(userId=user_id, conversation=[])
                session.add(new_conversation)
                await session.commit()
                return []
            
            conversation_data = conversation_row.conversation if conversation_row else []
            print(f"Raw conversation data: {conversation_data}")
            
            # Make sure we're working with an array
            if not isinstance(conversation_data, list):
                print(f"Warning: conversation_data is not a list. Type: {type(conversation_data)}")
                conversation_data = []
                
            # Return the data directly - it should already be in the correct format
            return conversation_data
        except Exception as e:
            print(f"🔥 Error fetching user conversation: {e}")
            traceback.print_exc()
            return []


async def append_to_user_conversation(user_id: str, user_message: str, agent_message: str):
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
                    userId=user_id,
                    conversation=new_conversation  # This is a list/array in Python but a JSONB in PostgreSQL
                )
                session.add(conversation_record)
            else:
                # Update existing record
                print(f"Updating existing conversation for user: {user_id}")
                # Ensure conversation is initialized as a list if None
                current_conversation = conversation_record.conversation or []
                
                # Important: Ensure we're working with a list
                if not isinstance(current_conversation, list):
                    print(f"WARNING: conversation is not a list: {type(current_conversation)}")
                    current_conversation = []
                
                # Append new messages to the list
                current_conversation.append(user_message_entry)
                current_conversation.append(agent_message_entry)
                
                # Update the conversation field
                conversation_record.conversation = current_conversation
            
            # Commit changes
            await session.commit()
            print(f"Successfully appended messages for user: {user_id}")
            
    except Exception as e:
        print(f"Error appending to conversation: {e}")
        traceback.print_exc()
        raise


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

# Core logic for handling agent response
# async def get_agent_response(user_id: str, user_prompt: str) -> str:
#     try:
#         # Retrieve conversation from PostgreSQL
#         print(f"Fetching conversation for user_id: {user_id}")
#         messages = await get_user_conversation(user_id)

#         print("Raw messages:", messages)

#         history = "\n".join([
#             f"{message.get('role', 'user').capitalize()}: {message.get('content', '')}"
#             for message in messages if isinstance(message, dict)
#         ])

#         conversation = history + (f"\nUser: {user_prompt}" if history else f"User: {user_prompt}")
#         print("Formatted conversation:")
#         print(conversation)

#         # Set up the agent
#         framework = "smolagents"
#         # setup_tracing(framework)
        
#         instructions = """
#             You are an empathetic Nutritionist and Exercise Science AI.
#             Your communication is friendly, concise, and professional.
#             Prioritize asking questions to gather critical information before offering advice.
#             Keep responses under 2-3 sentences unless the user requests details.
#         """

#         # Ensure that AnyAgent.create handles async properly
#         agent = AnyAgent.create(
#             framework,
#             AgentConfig(
#                 model_id="gpt-4.1-nano",
#                 instructions=instructions,
#                 tools=[search_web, visit_webpage]
#             )
#         )

#         print("Running agent...")

#         # If agent.run is async, simply await it
#         result = agent.run(conversation)

#         print("Agent response:")
#         print(result)

#         html = format_response_as_html(result)

#         await append_to_user_conversation(user_id, user_prompt, html)
#         return html

#     except Exception as e:
#         print(f"Error in get_agent_response for user_id={user_id}: {e}")
#         traceback.print_exc()  # <- THIS gives the full stack trace
#         return "<p>Oops! Something went wrong. Please try again later.</p>"


# Core logic for handling agent response
async def get_agent_response(user_id: str, user_prompt: str) -> str:
    try:
        # Retrieve conversation from PostgreSQL
        print(f"Fetching conversation for user_id: {user_id}")
        messages = await get_user_conversation(user_id)

        print(f"Raw messages: {type(messages)} containing {len(messages) if messages else 0} items")
        if messages and len(messages) > 0:
            print(f"First message sample: {messages[0]}")

        # Format conversation for OpenAI ChatGPT
        openai_messages = []
        
        # Add system message with instructions
        openai_messages.append({
            "role": "system", 
            "content": """You are an expert AI coach specializing in integrated nutrition and exercise science. 
            Your communication is supportive yet authoritative, blending warmth with evidence-based guidance. 
            Balance conversational friendliness with scientific precision. 
            Keep initial responses under 3-4 sentences, expanding only when users request details."

            Process Rules:

            Phase 1: Strategic Assessment

            Collect essential data through conversational questioning:

            Baseline metrics: Age, height, weight, activity level
            Primary goal and motivation (weight management, performance, energy, etc.)
            Current nutrition habits (meal frequency, protein intake, hydration)
            Exercise experience and preferences (equipment access, time availability)
            Key obstacles (time constraints, dietary preferences, injuries)


            Use progressive questioning techniques:
            Start broad: "What's your main health goal right now?"
            Follow with specificity: "On a typical day, how many meals do you eat and what's your protein source?"
            Connect domains: "How does your current eating pattern align with your workout schedule?"

            Phase 2: Integrated Plan Development
            Create nutrition and exercise recommendations as complementary systems, not separate domains
            Emphasize how nutritional timing supports exercise performance
            Provide specific macronutrient targets based on exercise demands
            Include recovery strategies that blend nutrition and movement
            Offer behavioral strategies for habit integration

            Specialized Knowledge Application:
            Apply exercise science principles to nutrition advice (protein timing, workout fueling)
            Reference specific mechanisms (e.g., muscle protein synthesis, glycogen replenishment)
            Include practical implementation details (meal prep strategies, workout structuring)
            Adapt recommendations based on individual constraints (equipment, time, cooking ability)

            Personalization Approach:
            Link recommendations to stated goals using clear cause-effect relationships
            Acknowledge the interconnection between nutrition choices and workout performance
            Provide contingency options for common adherence challenges
            Use progressive complexity—start with foundational changes before advanced strategies

            Constraints:
            Never provide generic meal plans or workout routines—all advice must connect to specific user inputs
            Always explain the "why" behind recommendations, linking to both nutrition and exercise science
            When users request changes to their plan, analyze the impact on both nutritional and exercise components
            If safety concerns arise, clearly state limitations and recommend professional consultation
            """
        })
        
        # Add past conversation messages
        if messages and isinstance(messages, list):
            for message in messages:
                if isinstance(message, dict):
                    role = message.get('role')
                    # Skip messages with invalid roles
                    if role not in ["user", "assistant"]:
                        continue
                    openai_messages.append({
                        "role": role,
                        "content": message.get('content', '')
                    })
        
        # Add the current user message
        openai_messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        print(f"Sending {len(openai_messages)} messages to OpenAI")
        
        # Call OpenAI API
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",  # Use gpt-3.5-turbo for a less expensive option
                messages=openai_messages,
                temperature=0.7,
                max_tokens=300,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract the response text
            result = response.choices[0].message.content
            print("ChatGPT response:", result)
            
        except Exception as openai_error:
            print(f"OpenAI API error: {openai_error}")
            traceback.print_exc()
            result = "I'm having trouble connecting to my knowledge base right now. Could you please try again in a moment?"

        # Format as HTML
        html = format_response_as_html(result)
        print("HTML formatted response:")
        print(html)

        # Save the conversation
        await append_to_user_conversation(user_id, user_prompt, html)
        return html

    except Exception as e:
        print(f"Error in get_agent_response for user_id={user_id}: {e}")
        traceback.print_exc()  # Print the full stack trace
        return "<p>Oops! Something went wrong. Please try again later.</p>"


# Routes
@app.post("/submit-prompt")
async def submit_prompt(data: PromptRequest):
    try:
        response = await get_agent_response(data.user_id, data.user_prompt)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Retrieve the conversation for the session
@app.get("/get-conversation/{user_id}")
async def get_conversation(user_id: str):
    try:
        messages = await get_user_conversation(user_id)
        print(f"Returning conversation with {len(messages)} messages")
        return {"conversation": messages}
    except Exception as e:
        print(f"Error in get_conversation endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")


# Add this to your startup event
@app.on_event("startup")
async def startup():
    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Check if we need to initialize default conversation records
        async with SessionLocal() as session:
            # Helper function to add a test user if needed
            async def ensure_user_exists(user_id):
                result = await session.execute(
                    select(Conversation).where(Conversation.userId == user_id)
                )
                user = result.scalars().first()
                
                if not user:
                    print(f"Creating new conversation record for user: {user_id}")
                    new_user = Conversation(
                        userId=user_id,
                        conversation=[]  # Empty conversation array
                    )
                    session.add(new_user)
                    return True
                return False
            
            # Ensure some common user IDs exist
            changes = False
            changes |= await ensure_user_exists("guest")
            changes |= await ensure_user_exists("test-user")
            
            if changes:
                await session.commit()
                
        print("Database setup completed successfully")
    except Exception as e:
        print(f"Error during startup: {e}")
        import traceback
        traceback.print_exc()




@app.get("/test-agent/{user_id}")
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