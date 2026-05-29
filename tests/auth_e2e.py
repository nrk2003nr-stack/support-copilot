import requests
import time
import sys

BASE = "http://127.0.0.1:8000/api"

def run():
    ts = int(time.time())
    email = f"e2e_test_{ts}@example.com"
    password = "E2EPassword123!"
    full_name = "E2E Test"

    print("Registering user", email)
    r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": password, "full_name": full_name, "role": "user"})
    if r.status_code not in (200,201):
        print("Register failed:", r.status_code, r.text)
        sys.exit(1)
    data = r.json()
    if "access_token" in data:
        token = data["access_token"]
        print("Got tokens from register.")
    else:
        print("Register returned user only; logging in to obtain tokens.")
        r2 = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
        if r2.status_code != 200:
            print("Login after register failed:", r2.status_code, r2.text)
            sys.exit(1)
        token = r2.json().get("access_token")

    print("Calling /auth/me with token")
    r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        print("/auth/me failed:", r.status_code, r.text)
        sys.exit(1)
    me = r.json()
    if me.get("email") != email:
        print("/auth/me returned wrong user:", me)
        sys.exit(1)
    print("/auth/me returned correct user.")

    print("Logging in")
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        print("Login failed:", r.status_code, r.text)
        sys.exit(1)
    print("Login returned tokens.")

    print("All auth E2E checks passed.")

if __name__ == '__main__':
    run()
