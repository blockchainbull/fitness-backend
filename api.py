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
                select(Conversation.conversation).where(Conversation.userId == user_id)
            )
            conversation_data = result.scalar() or []

            formatted_conversation = []
            for entry in conversation_data:
                role = entry.get("role", "unknown")
                content = entry.get("content", "")
                timestamp = entry.get("timestamp", "")
                formatted_conversation.append({
                    "role": role,
                    "content": content,
                    "timestamp": timestamp
                })
            return formatted_conversation
        except Exception as e:
            print(f"🔥 Error fetching user conversation: {e}")
            raise

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

    async with SessionLocal() as session:
        # First, retrieve the current conversation array
        result = await session.execute(
            select(Conversation.conversation)
            .where(Conversation.userId == user_id)
        )
        conversation_data = result.scalar() or []

        # Append the new user and assistant messages to the array
        conversation_data.append(user_message_entry)
        conversation_data.append(agent_message_entry)

        # Update the conversation in the database
        stmt = (
            update(Conversation)
            .where(Conversation.userId == user_id)
            .values(conversation=conversation_data)
        )
        await session.execute(stmt)
        await session.commit()

# Core logic for handling agent response
async def get_agent_response(user_id: str, user_prompt: str) -> str:
    try:
        # Retrieve conversation from PostgreSQL
        print(f"Fetching conversation for user_id: {user_id}")
        messages = await get_user_conversation(user_id)

        print("Raw messages:", messages)

        history = "\n".join([
            f"{message.get('role', 'user').capitalize()}: {message.get('content', '')}"
            for message in messages if isinstance(message, dict)
        ])

        conversation = history + (f"\nUser: {user_prompt}" if history else f"User: {user_prompt}")
        print("Formatted conversation:")
        print(conversation)

        # Set up the agent
        framework = "smolagents"
        # setup_tracing(framework)
        
        instructions = """
            You are an empathetic Nutritionist and Exercise Science AI.
            Your communication is friendly, concise, and professional.
            Prioritize asking questions to gather critical information before offering advice.
            Keep responses under 2-3 sentences unless the user requests details.
        """

        # Ensure that AnyAgent.create handles async properly
        agent = AnyAgent.create(
            framework,
            AgentConfig(
                model_id="gpt-4.1-nano",
                instructions=instructions,
                tools=[search_web, visit_webpage]
            )
        )

        print("Running agent...")

        # If agent.run is async, simply await it
        result = agent.run(conversation)

        print("Agent response:")
        print(result)

        html = format_response_as_html(result)

        await append_to_user_conversation(user_id, user_prompt, html)
        return html

    except Exception as e:
        print(f"Error in get_agent_response for user_id={user_id}: {e}")
        traceback.print_exc()  # <- THIS gives the full stack trace
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
        conversation = []
        for content, in messages:
            conversation.append({"content": content})
        return {"conversation": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")
