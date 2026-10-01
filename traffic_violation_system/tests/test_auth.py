from fastapi.testclient import TestClient


def test_login_and_me(client: TestClient, admin_user) -> None:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "TestPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == admin_user.username
    assert me.json()["role"] == "ADMIN"


def test_protected_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/cameras")
    assert response.status_code == 401
