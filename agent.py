"""
Agent implementation for generating responses to user prompts.
"""
from config import client_openai, SYSTEM_PROMPT, MODEL_NAME
from utils import format_response_as_html
from database import get_user_conversation, append_to_user_conversation, get_user_profile, get_user_notes, add_or_update_user_note
from tasks import queue_task
import json
import traceback


async def extract_user_notes(user_id: str, user_prompt: str, agent_response: str):
    """
    Extract structured notes from user conversation using OpenAI.
    """
    try:
        # Get recent conversation for context
        messages = await get_user_conversation(user_id)
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        
        # Format conversation for analysis
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown').upper()}: {msg.get('content', '')}"
            for msg in recent_messages
        ])
        
        # Add the current interaction
        conversation_text += f"\nUSER: {user_prompt}\nASSISTANT: {agent_response}"
        
        # Create analysis prompt
        analysis_prompt = f"""
        You are a professional nutritionist and fitness expert. Review this conversation and extract key information about the client in a structured JSON format.
        
        Focus on extracting:
        
        1. Dietary information (preferences, restrictions, current diet patterns)
        2. Fitness goals (weight loss, muscle gain, endurance, specific targets)
        3. Current exercise habits (frequency, type, intensity)
        4. Metrics (current weight, target weight, measurements)
        5. Lifestyle factors (sleep, stress, time constraints)
        6. Health concerns or limitations
        7. Health metrics (if mentioned: BMR, BMI, body fat, etc.)
        
        Format your response as valid JSON like this:
        {{
          "notes": [
            {{"category": "dietary_preference", "key": "protein_intake", "value": "60g daily", "confidence": 0.9, "source": "user_stated"}},
            {{"category": "fitness_goal", "key": "weight_loss", "value": "10 pounds in 3 months", "confidence": 0.8, "source": "user_stated"}},
            {{"category": "health_metric", "key": "current_weight", "value": "180 pounds", "confidence": 0.95, "source": "user_stated"}},
            ...
          ]
        }}
        
        Use these categories:
        - dietary_preference
        - dietary_restriction
        - fitness_goal
        - exercise_habit
        - physical_metric
        - health_metric
        - lifestyle_factor
        - health_concern
        
        If you're uncertain about any information, use a lower confidence score. Only include information that was explicitly mentioned or can be reasonably inferred.
        
        Conversation:
        {conversation_text}
        """
        
        # Call OpenAI API for analysis
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",  # Can use a smaller model for cost savings
            messages=[
                {"role": "system", "content": "You extract structured information from conversations."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_tokens=1000
        )
        
        # Parse the response
        try:
            result_text = response.choices[0].message.content
            # Extract JSON portion (in case there's extra text)
            json_str = result_text
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                json_str = result_text.split("```")[1].split("```")[0]
                
            result = json.loads(json_str)
            
            # Store the notes in the database
            if "notes" in result and isinstance(result["notes"], list):
                for note in result["notes"]:
                    await add_or_update_user_note(
                        user_id=user_id,
                        category=note.get("category", "other"),
                        key=note.get("key", "unknown"),
                        value=note.get("value", ""),
                        confidence=note.get("confidence", 0.5),
                        source=note.get("source", "inferred")
                    )
                    
                print(f"Extracted and stored {len(result['notes'])} notes for user {user_id}")
                return result["notes"]
            else:
                print("No notes found in extraction result")
                return []
                
        except json.JSONDecodeError as e:
            print(f"Error parsing notes JSON: {e}")
            print(f"Raw response: {result_text}")
            return []
            
    except Exception as e:
        print(f"Error in note extraction: {e}")
        traceback.print_exc()
        return []

async def get_agent_response(user_id: str, user_prompt: str) -> str:
    """
    Process a user's prompt and generate an appropriate agent response
    with personalized context from user profile and notes.
    """
    try:
        # Retrieve conversation history
        print(f"Fetching conversation for user_id: {user_id}")
        messages = await get_user_conversation(user_id)
        
        # Get user profile data
        print(f"Fetching profile for user_id: {user_id}")
        user_profile = await get_user_profile(user_id)
        print("== User Profile ==")
        print(user_profile)
        
        # Get user notes
        user_notes = await get_user_notes(user_id)
        print("== User Notes ==")
        print(user_notes)
        
        # Format conversation for OpenAI ChatGPT
        openai_messages = []
        
        # Create enhanced system prompt with user context
        user_context = "USER PROFILE INFORMATION:\n"
        
        # Add user profile information
        if user_profile:
            user_context += f"- Name: {user_profile.get('name', 'Not provided')}\n"
            
            # Physical stats
            physical_stats = user_profile.get('physicalStats', {})
            preferences = user_profile.get('preferences', {})
            measurement_unit = preferences.get('measurementUnit', 'metric')
            
            if physical_stats:
                user_context += f"- Age: {physical_stats.get('age', 'Not provided')}\n"
                
                height = physical_stats.get('height')
                if height:
                    height_unit = 'inches' if measurement_unit == 'imperial' else 'cm'
                    user_context += f"- Height: {height} {height_unit}\n"
                else:
                    user_context += "- Height: Not provided\n"
                
                weight = physical_stats.get('weight')
                if weight:
                    weight_unit = 'lbs' if measurement_unit == 'imperial' else 'kg'
                    user_context += f"- Weight: {weight} {weight_unit}\n"
                else:
                    user_context += "- Weight: Not provided\n"
                
                user_context += f"- Gender: {physical_stats.get('gender', 'Not provided')}\n"
                user_context += f"- Activity Level: {physical_stats.get('activityLevel', 'Not provided')}\n"
            
            # Reproductive health information (for female users)
            gender = user_profile.get('gender') or physical_stats.get('gender', '').lower()
            if gender and gender.lower() == 'female':
                user_context += "\nREPRODUCTIVE HEALTH INFORMATION:\n"
                
                has_periods = user_profile.get('has_periods')
                if has_periods is not None:
                    user_context += f"- Currently has menstrual periods: {'Yes' if has_periods else 'No'}\n"
                    
                    if has_periods:
                        # Add period-specific information
                        last_period_date = user_profile.get('last_period_date')
                        if last_period_date:
                            # Format the date nicely
                            try:
                                from datetime import datetime
                                if isinstance(last_period_date, str):
                                    last_period = datetime.fromisoformat(last_period_date.replace('Z', '+00:00')).strftime('%B %d, %Y')
                                else:
                                    last_period = last_period_date.strftime('%B %d, %Y')
                                user_context += f"- Last period date: {last_period}\n"
                            except:
                                user_context += f"- Last period date: {last_period_date}\n"
                        
                        cycle_length = user_profile.get('cycle_length')
                        if cycle_length:
                            user_context += f"- Average cycle length: {cycle_length} days\n"
                        
                        cycle_regular = user_profile.get('cycle_length_regular')
                        if cycle_regular is not None:
                            user_context += f"- Cycle regularity: {'Regular' if cycle_regular else 'Irregular'}\n"
                        
                        pregnancy_status = user_profile.get('pregnancy_status')
                        if pregnancy_status and pregnancy_status != 'prefer_not_to_say':
                            status_map = {
                                'not_pregnant': 'Not pregnant',
                                'pregnant': 'Currently pregnant',
                                'breastfeeding': 'Currently breastfeeding',
                                'trying_to_conceive': 'Trying to conceive',
                                'rather_not_say':'Rather not say'
                            }
                            readable_status = status_map.get(pregnancy_status, pregnancy_status.replace('_', ' ').title())
                            user_context += f"- Current status: {readable_status}\n"
                    
                    tracking_preference = user_profile.get('period_tracking_preference')
                    if tracking_preference:
                        pref_map = {
                            'track_periods': 'Wants period tracking features',
                            'general_wellness': 'Interested in general wellness support',
                            'no_tracking': 'Prefers no period-related features'
                        }
                        readable_pref = pref_map.get(tracking_preference, tracking_preference.replace('_', ' ').title())
                        user_context += f"- Tracking preference: {readable_pref}\n"
                else:
                    user_context += "- Reproductive health information: Not provided during onboarding\n"

            # Add health metrics if available
            health_metrics = user_profile.get('healthMetrics', {})
            if health_metrics:
                user_context += "\nHEALTH METRICS:\n"
                
                bmr = health_metrics.get('bmr')
                if bmr:
                    user_context += f"- Basal Metabolic Rate (BMR): {bmr} calories/day\n"
                
                tdee = health_metrics.get('tdee')
                if tdee:
                    user_context += f"- Total Daily Energy Expenditure (TDEE): {tdee} calories/day\n"
                
                bmi = health_metrics.get('bmi')
                if bmi:
                    user_context += f"- Body Mass Index (BMI): {bmi}\n"
                
                body_fat = health_metrics.get('bodyFatPercentage')
                if body_fat:
                    user_context += f"- Estimated Body Fat: {body_fat}%\n"
                
                lbm = health_metrics.get('lbm')
                if lbm:
                    lbm_unit = 'lbs' if measurement_unit == 'imperial' else 'kg'
                    user_context += f"- Lean Body Mass (LBM): {lbm} {lbm_unit}\n"
            
            # Fitness goal and dietary preferences
            user_context += f"\n- Fitness Goal: {user_profile.get('fitnessGoal', 'Not provided')}\n"
            
            dietary_prefs = user_profile.get('dietaryPreferences', [])
            if dietary_prefs:
                user_context += f"- Dietary Preferences: {', '.join(dietary_prefs)}\n"
            else:
                user_context += "- Dietary Preferences: None specified\n"
        
        # Add user notes grouped by category
        if user_notes:
            user_context += "\nUSER NOTES FROM PREVIOUS CONVERSATIONS:\n"
            
            # Group notes by category
            notes_by_category = {}
            for note in user_notes:
                category = note.category
                if category not in notes_by_category:
                    notes_by_category[category] = []
                notes_by_category[category].append(note)
            
            # Add notes by category
            for category, notes in notes_by_category.items():
                category_display = category.replace('_', ' ').title()
                user_context += f"\n{category_display}:\n"
                
                # Only include high confidence notes or limit to top 3 per category
                sorted_notes = sorted(notes, key=lambda n: n.confidence, reverse=True)[:5]
                for note in sorted_notes:
                    if note.confidence >= 0.5:  # Only include reasonable confidence notes
                        user_context += f"- {note.key}: {note.value}\n"
        
        # Add system message with instructions and user context
        system_prompt = f"{user_context}\n\n{SYSTEM_PROMPT}"
         
        openai_messages.append({
            "role": "system", 
            "content": system_prompt
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
        
        # Right before the OpenAI API call in get_agent_response function
        print("\n=== USER CONTEXT AND SYSTEM PROMPT ===")
        print(system_prompt)
        print("\n=== USER QUESTION ===")
        print(user_prompt)
        print("\n=== CONVERSATION HISTORY LENGTH ===")
        print(f"Using {len(openai_messages)} messages in conversation history")


        # Call OpenAI API
        result = ""
        try:
            response = client_openai.chat.completions.create(
                model=MODEL_NAME,
                messages=openai_messages,
                temperature=0.7,
                max_tokens=500,
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
        html_response = format_response_as_html(result)
        print("HTML formatted response:")
        print(html_response)

        # Save the conversation
        await append_to_user_conversation(user_id, user_prompt, html_response)
        
        # Extract notes in the background (don't await to avoid delaying response)
        # We'll use a background task or process for this in production
        # For now, we'll just run it after sending the response
        await queue_task(extract_user_notes, user_id, user_prompt, result)
        
        return html_response

    except Exception as e:
        print(f"Error in get_agent_response for user_id={user_id}: {e}")
        traceback.print_exc()
        return "<p>Oops! Something went wrong. Please try again later.</p>"
