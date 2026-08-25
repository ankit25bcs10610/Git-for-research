import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_user_route_returns_created_user():
    username = f"researcher-{uuid.uuid4()}"

    response = client.post("/api/users", json={"username": username, "display_name": "Ada"})

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == username
    assert body["display_name"] == "Ada"
    assert "id" in body


def test_create_user_route_defaults_display_name():
    username = f"researcher-{uuid.uuid4()}"

    response = client.post("/api/users", json={"username": username})

    assert response.status_code == 200
    assert response.json()["display_name"] == username


def test_create_user_route_conflicts_on_duplicate_username():
    username = f"researcher-{uuid.uuid4()}"
    client.post("/api/users", json={"username": username})

    response = client.post("/api/users", json={"username": username})

    assert response.status_code == 409


def test_list_users_route_includes_created_user():
    username = f"researcher-{uuid.uuid4()}"
    client.post("/api/users", json={"username": username})

    response = client.get("/api/users")

    assert response.status_code == 200
    usernames = [u["username"] for u in response.json()]
    assert username in usernames
