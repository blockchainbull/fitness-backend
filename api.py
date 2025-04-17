from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv
from collections import defaultdict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, select
import datetime
import os
import re
import agentops
from agents import Agent, Runner, WebSearchTool
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from markupsafe import escape

# Load environment variables
load_dotenv()

# Database and API config
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

# Initialize tools and clients
agentops.init(AGENTOPS_API_KEY)
client_openai = OpenAI()
web_search = WebSearchTool()

# SQLAlchemy setup
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String)
    content = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

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

# Agent setup
nutrition_and_fitness_coach = Agent(
    name="nutrition_and_fitness_coach",
    instructions="""You are an empathetic Nutritionist and Exercise Science AI.
    Your communication is friendly, concise, and professional.
    Prioritize asking questions to gather critical information before offering advice.
    Keep responses under 2-3 sentences unless the user requests details.
    """,
    tools=[web_search]
)

AGENTS = {
    "nutrition_and_fitness_coach": nutrition_and_fitness_coach,
}

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
    session_id: str
    user_prompt: str
    agent_name: str

# DB functions - FIXED
async def get_session_conversation(session_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            select(ChatMessage.role, ChatMessage.content, ChatMessage.created_at)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return result.all()

# FIXED to properly handle timestamps
async def append_to_session_conversation(session_id: str, user_message: str, agent_message: str):
    now = datetime.datetime.utcnow()
    
    async with SessionLocal() as session:
        # Add both user message and agent response with same timestamp
        session.add_all([
            ChatMessage(
                session_id=session_id, 
                role="user", 
                content=user_message,
                created_at=now
            ),
            ChatMessage(
                session_id=session_id, 
                role="assistant", 
                content=agent_message,
                created_at=now + datetime.timedelta(milliseconds=1)  # Ensure order is maintained
            ),
        ])
        await session.commit()

# Core logic - FIXED to handle PostgreSQL conversation format
async def get_agent_response(session_id: str, agent: Agent, user_prompt: str) -> str:
    # Retrieve conversation from PostgreSQL
    messages = await get_session_conversation(session_id)
    
    # Format conversation for the agent - now handling the (role, content, timestamp) tuples correctly
    history = "\n".join([f"{role.capitalize()}: {content}" for role, content, _ in messages])
    
    # Add the current user message
    conversation = history + (f"\nUser: {user_prompt}" if history else f"User: {user_prompt}")
    
    # Run the agent
    result = await Runner.run(agent, conversation)
    response = result.final_output
    
    # Format response as HTML
    html = format_response_as_html(response)
    
    # Store both user input and agent response
    await append_to_session_conversation(session_id, user_prompt, html)
    
    return html

# Routes
@app.post("/submit-prompt")
async def submit_prompt(data: PromptRequest):
    agent = AGENTS.get(data.agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    try:
        response = await get_agent_response(data.session_id, agent, data.user_prompt)
        return {"response": response}
    except Exception as e:
        print(f"Error occurred while processing prompt: {e}")  # Add logging for debugging
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# FIXED to match the MongoDB return format expected by frontend
@app.get("/get-conversation/{session_id}")
async def get_conversation(session_id: str):
    try:
        # Retrieve session conversation from PostgreSQL
        messages = await get_session_conversation(session_id)
        
        # Format the messages in the same structure as the MongoDB version expected
        conversation = []
        for role, content, created_at in messages:
            # Format timestamp to match your frontend expectations
            timestamp = created_at.isoformat() if created_at else ""
            
            conversation.append({
                "role": role,
                "content": content,
                "timestamp": timestamp
            })

        return {"conversation": conversation}
    except Exception as e:
        print(f"Error retrieving conversation: {e}")  # Add logging for debugging
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")

# Add a startup event to create tables if they don't exist
@app.on_event("startup")
async def startup():
    try:
        # Create a connection and the database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error during startup: {e}")