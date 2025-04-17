from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict
import agentops
from agents import Agent, Runner, WebSearchTool
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from markupsafe import escape
import re

# Load environment variables
load_dotenv()

# Get API keys and MongoDB URI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")
MONGO_URI = "mongodb+srv://bulli007:123456ABCDEF@cluster0.mvxqc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGO_DB_NAME = "ai_coach"

# Initialize MongoDB
client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
sessions_collection = db["conversation"]

# Initialize AgentOps and OpenAI
agentops.init(AGENTOPS_API_KEY)
client_openai = OpenAI()
web_search = WebSearchTool()

# In-memory session context
session_memory = defaultdict(list)
MAX_HISTORY = 10

# HTML formatter
def format_response_as_html(text: str) -> str:
    lines = text.strip().splitlines()
    html = []
    in_ul = False
    in_ol = False

    for line in lines:
        stripped = line.strip()

        # Remove ** enclosing content
        if stripped.startswith("**") and stripped.endswith("**"):
            stripped = stripped[2:-2].strip()

        # Headings
        if stripped.startswith("### "):
            html.append(f"<h3>{escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            html.append(f"<h2>{escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            html.append(f"<h1>{escape(stripped[2:])}</h1>")

        # Unordered list (handle multiple list items starting with -)
        elif stripped.startswith("- "):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{escape(stripped[2:])}</li>")

        # Ordered list
        elif re.match(r"^\d+\.\s", stripped):
            if not in_ol:
                html.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s", "", stripped)
            html.append(f"<li>{escape(item)}</li>")

        # Key: Value pairs
        elif ":" in stripped and not stripped.startswith("http"):
            key, value = stripped.split(":", 1)
            html.append(f"<p><strong>{escape(key.strip())}:</strong> {escape(value.strip())}</p>")

        # Empty line (convert to <br>)
        elif not stripped:
            if in_ul:
                html.append("</ul>")
                in_ul = False
            if in_ol:
                html.append("</ol>")
                in_ol = False
            html.append("<br>")

        # Plain paragraph
        else:
            html.append(f"<p>{escape(stripped)}</p>")

    # Close any open lists
    if in_ul:
        html.append("</ul>")
    if in_ol:
        html.append("</ol>")

    return "\n".join(html)

# Request model for API endpoint
class PromptRequest(BaseModel):
    session_id: str
    user_prompt: str
    agent_name: str

# MongoDB Functions
async def get_session_conversation(session_id: str):
    session = await sessions_collection.find_one({"session_id": session_id})
    if session:
        return session["conversation"]
    return []

async def update_session_conversation(session_id: str, conversation: list):
    await sessions_collection.update_one(
        {"session_id": session_id},
        {"$set": {"conversation": conversation}},
        upsert=True
    )

async def append_to_session_conversation(session_id: str, user_message: str, agent_message: str):
    session_conversation = await get_session_conversation(session_id)
    session_conversation.append(f"User: {user_message}")
    session_conversation.append(f"Agent: {agent_message}")

    # Limit the conversation length (e.g., last 20 messages)
    if len(session_conversation) > 40:  # 2 messages per interaction
        session_conversation = session_conversation[-40:]

    await update_session_conversation(session_id, session_conversation)

# Response models for structured outputs
class NutritionInfo(BaseModel):
    foods: List[str] = Field(..., description="List of foods identified in the meal")
    total_calories: Optional[int] = Field(None, description="Estimated total calories")
    recommendations: Optional[List[str]] = Field(None, description="Nutritional recommendations")

class WorkoutPlan(BaseModel):
    exercises: List[str] = Field(..., description="List of recommended exercises")
    duration: str = Field(..., description="Recommended workout duration")
    intensity: str = Field(..., description="Recommended intensity level")

nutrition_and_fitness_coach = Agent(
    name="nutrition_and_fitness_coach",
    instructions="""You are an empathetic Nutritionist and Exercise Science AI. 
    Your communication is friendly, concise, and professional. 
    Prioritize asking questions to gather critical information before offering advice. 
    Keep responses under 2-3 sentences unless the user requests details.
    """,
    tools=[web_search]
)

# Map agent name to instance
AGENTS = {
    "nutrition_and_fitness_coach": nutrition_and_fitness_coach,
}

# FastAPI app initialization
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run the agent and manage session memory
async def get_agent_response(session_id: str, agent: Agent, user_prompt: str) -> str:
    # Retrieve session conversation from MongoDB
    session_conversation = await get_session_conversation(session_id)
    
    # Build full conversation context
    conversation = "\n".join(session_conversation) + f"\nUser: {user_prompt}"
    
    # Run the agent
    result = await Runner.run(agent, conversation)
    raw_response = result.final_output

    # Append user message and raw (not HTML) agent response to the DB
    html_response = format_response_as_html(raw_response)
    await append_to_session_conversation(session_id, user_prompt, html_response)

    # Format agent response to HTML for frontend use

    print(html_response)
    return html_response

# API endpoint to handle user input
@app.post("/submit-prompt")
async def submit_prompt(data: PromptRequest):
    agent = AGENTS.get(data.agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    try:
        response = await get_agent_response(data.session_id, agent, data.user_prompt)
        return {"response": response}
    except Exception as e:
        # Log the error with more details for debugging
        print(f"Error occurred while processing prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# New endpoint to retrieve previous chat history
@app.get("/get-conversation/{session_id}")
async def get_conversation(session_id: str):
    try:
        # Retrieve session conversation from MongoDB
        session_conversation = await get_session_conversation(session_id)
        if not session_conversation:
            return {"message": "No previous conversation found."}

        # Return the conversation in the proper format
        conversation = []
        for i in range(0, len(session_conversation), 2):
            user_message = session_conversation[i]
            agent_message = session_conversation[i + 1] if i + 1 < len(session_conversation) else ''
            conversation.append({
                "role": "user",
                "content": user_message.split(": ", 1)[1] if user_message else "",
                "timestamp": user_message.split(" - ", 1)[0] if user_message else ""
            })
            conversation.append({
                "role": "assistant",
                "content": agent_message.split(": ", 1)[1] if agent_message else "",
                "timestamp": agent_message.split(" - ", 1)[0] if agent_message else ""
            })

        return {"conversation": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")