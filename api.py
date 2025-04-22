"""
API routes for the nutrition and exercise coach application.
"""
from fastapi import APIRouter, HTTPException
import traceback

from models import PromptRequest, ConversationResponse
from agent import get_agent_response
from database import get_user_conversation

# Create router
router = APIRouter()


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