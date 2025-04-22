"""
Agent implementation for generating responses to user prompts.
"""
import traceback
from typing import List, Dict, Any

from config import client_openai, SYSTEM_PROMPT, MODEL_NAME
from utils import format_response_as_html
from database import get_user_conversation, append_to_user_conversation


async def get_agent_response(user_id: str, user_prompt: str) -> str:
    """
    Process a user's prompt and generate an appropriate agent response.
    
    Args:
        user_id: The unique identifier for the user
        user_prompt: The user's message
        
    Returns:
        HTML-formatted response from the agent
    """
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
            "content": SYSTEM_PROMPT
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
                model=MODEL_NAME,
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


# PRESERVED COMMENTED CODE: Legacy agent implementation
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
#         return "<p>Oops! Something went wrong. Please try again later.</p>"         #