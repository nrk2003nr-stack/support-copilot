import requests
import time
BASE = 'http://127.0.0.1:8000/api'
email = f"tmp_{int(time.time())}@example.com"
payload = {"email": email, "password": "Testpass123!", "full_name": "Tmp"}
print('POST', BASE + '/auth/register', payload)
r = requests.post(BASE + '/auth/register', json=payload)
print('Status:', r.status_code)
print('Headers:', r.headers)
try:
    print('JSON:', r.json())
except Exception as e:
    print('Text:', r.text)
