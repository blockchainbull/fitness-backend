import requests
import json

# API endpoint URL
url = "http://localhost:5000/api/agent"

# Example request to the health coach
health_coach_request = {
    "user_prompt": "I want to improve my diet. Can you suggest some healthy breakfast options?",
    "agent_name": "health_coach"
}

# Example request to the nutrition agent
nutrition_request = {
    "user_prompt": "Is pizza healthy?",
    "agent_name": "nutrition_agent"
}

# Function to make request and print response
def test_agent_api(request_data):
    print(f"Testing agent: {request_data['agent_name']}")
    print(f"Prompt: {request_data['user_prompt']}")
    
    try:
        # Make POST request to API
        response = requests.post(url, json=request_data)
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            print("\nAPI Response:")
            print(f"Agent: {result['agent']}")
            print(f"Response: {result['response']}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
    
    print("\n" + "-"*50 + "\n")

# Test both requests
if __name__ == "__main__":
    print("Testing Health and Wellness Agent API\n")
    test_agent_api(health_coach_request)
    test_agent_api(nutrition_request)