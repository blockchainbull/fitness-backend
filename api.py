"""
API routes for the nutrition and exercise coach application.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import traceback
from database import get_user_conversation, get_user_profile, get_user_notes
from agent import get_agent_response
from models import PromptRequest, ConversationResponse
from pydantic import BaseModel

# Create router
router = APIRouter()

# Define the login request body
class LoginRequest(BaseModel):
    email: str
    password: str



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