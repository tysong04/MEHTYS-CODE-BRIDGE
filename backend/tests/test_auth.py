import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import init_db, get_db_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM sessions;")
            conn.execute("DELETE FROM users;")
    finally:
        conn.close()


def test_register_and_login_flow():
    # Register a new user
    email = "developer@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={"name": "Dev User", "email": email, "password": "SuperSecretPassword123!"}
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["user"]["email"] == email
    assert reg_data["user"]["name"] == "Dev User"
    assert "token" in reg_data
    token = reg_data["token"]

    # Retrieve profile using bearer token
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # Login with valid credentials
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "SuperSecretPassword123!"}
    )
    assert login_res.status_code == 200
    login_token = login_res.json()["token"]

    # Logout
    logout_res = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {login_token}"}
    )
    assert logout_res.status_code == 200

    # Token should now be invalid
    invalid_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_token}"})
    assert invalid_me.status_code == 401


def test_register_duplicate_email():
    email = "duplicate@example.com"
    client.post(
        "/api/auth/register",
        json={"name": "First User", "email": email, "password": "Password123!"}
    )
    res = client.post(
        "/api/auth/register",
        json={"name": "Second User", "email": email, "password": "Password123!"}
    )
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]["message"]


def test_login_invalid_password():
    email = "security_test@example.com"
    client.post(
        "/api/auth/register",
        json={"name": "Sec User", "email": email, "password": "CorrectPassword123!"}
    )
    res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword999!"}
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]["message"]
