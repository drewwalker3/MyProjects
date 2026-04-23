import requests

url = "http://127.0.0.1:5000/chat"

payload = {
    "text": "Hey Jarvis, what was I working on?"
}

response = requests.post(url, json=payload)

print("Status code:", response.status_code)
print("Response text:")
print(response.text)

#cd /Users/andrewwalker/Desktop/jarvis-vr/python-backend && python3 test_chat.py

