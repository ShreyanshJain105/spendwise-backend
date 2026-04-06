import requests
import json

BASE = "http://localhost:5000/api"

def test_auth_flow():
    # 1. Sign up
    print("Testing Registration...")
    data = {"name": "Test User", "email": "debug@test.com", "password": "password123"}
    r = requests.post(f"{BASE}/auth/register", json=data)
    print(f"Register status: {r.status_code}")
    if r.status_code != 201:
        # Try login if already exists
        print("Registration failed, trying login...")
        r = requests.post(f"{BASE}/auth/login", json=data)
        print(f"Login status: {r.status_code}")
    
    res = r.json()
    if not res.get("ok"):
        print(f"Error: {res}")
        return

    token = res["data"]["token"]
    print(f"Token received: {token[:10]}...")

    # 2. Call /auth/me
    print("Testing /auth/me...")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE}/auth/me", headers=headers)
    print(f"Auth Me status: {r.status_code}")
    print(f"Auth Me response: {r.json()}")

    # 3. Call /accounts
    print("Testing /accounts...")
    r = requests.get(f"{BASE}/accounts", headers=headers)
    print(f"Accounts status: {r.status_code}")
    print(f"Accounts response: {r.json()}")

if __name__ == "__main__":
    test_auth_flow()
