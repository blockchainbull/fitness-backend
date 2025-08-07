"""
Pydantic models for request and response validation.
"""
from pydantic import BaseModel
from typing import List, Dict, Any


class PromptRequest(BaseModel):
    """
    Model for incoming prompt requests from users.
    """
    user_id: str
    user_prompt: str
    agent_name: str


class ConversationEntry(BaseModel):
    """
    Model for individual conversation messages.
    """
    role: str  
    content: str
    timestamp: str


class ConversationResponse(BaseModel):
    """
    Model for returning conversation history to clients.
    """
    conversation: List[Dict[str, Any]]