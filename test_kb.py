import requests
import json
import time

BASE_URL = "http://localhost:8002"

def test_kb():
    # 1. Login or get a token (assuming we have a user)
    # For testing, we can use a known user or skip if auth is complex in script
    # Let's try to register/login a test user
    
    test_user = {
        "email": f"kb_test_{int(time.time())}@example.com",
        "full_name": "KB Tester",
        "password": "Password123!",
        "role": "job_seeker",
        "mobile": "9876543210"
    }
    
    print(f"Registering user: {test_user['email']}")
    reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json=test_user)
    print(f"Register Resp: {reg_resp.status_code}")
    
    login_data = {"email": test_user["email"], "password": test_user["password"]}
    login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    print(f"Login Resp: {login_resp.status_code}")
    
    if login_resp.status_code != 200:
        print("Login failed")
        return
        
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Send a chat message
    chat_payload = {
        "message": "I want to search for Python developer jobs in Bangalore",
        "history": []
    }
    print("Sending chat message...")
    chat_resp = requests.post(f"{BASE_URL}/api/ai/chat", json=chat_payload, headers=headers)
    print(f"Chat Resp: {chat_resp.status_code}")
    if chat_resp.status_code == 200:
        try:
            print(f"AI Response: {chat_resp.json()['response'][:100]}...")
        except UnicodeEncodeError:
            print("AI Response received (unicode printing error in terminal)")
    else:
        print(f"Chat Error: {chat_resp.text}")
    
    # 3. Check knowledge base
    print("Retrieving knowledge base...")
    kb_resp = requests.get(f"{BASE_URL}/api/ai/knowledge-base", headers=headers)
    print(f"KB Resp Status: {kb_resp.status_code}")
    if kb_resp.status_code == 200:
        kb_data = kb_resp.json()
        print(f"KB Data: {json.dumps(kb_data, indent=2)}")
        if len(kb_data) > 0:
            print("SUCCESS: Knowledge base entry found!")
            print(f"Extracted Intent: {kb_data[0].get('intent')}")
        else:
            print("FAILURE: No KB data found")
    else:
        print(f"KB Error: {kb_resp.text}")

if __name__ == "__main__":
    test_kb()
