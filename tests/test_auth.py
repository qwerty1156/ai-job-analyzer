def test_register_creates_user(client):
    response = client.post("/register", json={"email": "new@example.com", "password": "password123"})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "hashed_password" not in data  # пароль никогда не возвращается


def test_register_duplicate_email_returns_409(client, user):
    response = client.post("/register", json={"email": user.email, "password": "password123"})
    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


def test_register_short_password_returns_400(client):
    response = client.post("/register", json={"email": "short@example.com", "password": "abc"})
    assert response.status_code == 400


def test_register_validation_error_never_echoes_password(client):
    """Pydantic обычно включает невалидное значение поля в errors() —
    для password это нельзя допускать ни в ответе, ни (тем более) в логах."""
    secret_attempt = "hunter2"  # < 8 символов -> провалит валидацию min_length
    response = client.post("/register", json={"email": "short2@example.com", "password": secret_attempt})
    assert response.status_code == 400
    assert secret_attempt not in response.text


def test_login_success_returns_token(client, user):
    response = client.post("/login", json={"email": user.email, "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 10


def test_login_wrong_password_returns_401(client, user):
    response = client.post("/login", json={"email": user.email, "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_login_unknown_email_returns_401(client):
    response = client.post("/login", json={"email": "ghost@example.com", "password": "whatever123"})
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, user, auth_headers):
    response = client.get("/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_me_rejects_invalid_token(client):
    response = client.get("/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
