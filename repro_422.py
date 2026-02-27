import requests
import json

url = "http://localhost:8002/api/ai/chat"
headers = {"Content-Type": "application/json"}

# Test 1: Simple message
print("Test 1: Simple message")
payload = {"message": "hello", "history": []}
try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Message with history
print("\nTest 2: Message with history")
payload = {
    "message": "how are you",
    "history": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
}
try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Malformed history (number instead of string)
print("\nTest 3: Malformed history (int value)")
payload = {
    "message": "test",
    "history": [{"role": "user", "content": 123}]
}
try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
