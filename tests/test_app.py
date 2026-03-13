import pytest
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


# ── Home page ──────────────────────────────────────────────────────────────────

def test_home_page_status(client):
    response = client.get("/")
    assert response.status_code == 200


def test_home_page_contains_categories(client):
    response = client.get("/")
    data = response.data.decode()
    for keyword in ("Networking", "Cisco", "Python", "Linux"):
        assert keyword in data


def test_home_page_contains_ai_chat_link(client):
    response = client.get("/")
    assert b"AI Chat" in response.data or b"ai-chat" in response.data.lower() or b"/chat" in response.data


# ── Category pages ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("category", ["networking", "cisco", "python", "linux"])
def test_category_page_ok(client, category):
    response = client.get(f"/category/{category}")
    assert response.status_code == 200


def test_category_page_lists_lessons(client):
    response = client.get("/category/networking")
    data = response.data.decode()
    assert "OSI" in data or "TCP" in data or "Subnet" in data


def test_category_invalid_returns_404(client):
    response = client.get("/category/nonexistent")
    assert response.status_code == 404


# ── Lesson pages ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("category,slug", [
    ("networking", "01_osi_model"),
    ("networking", "02_tcp_ip"),
    ("networking", "03_subnetting"),
    ("cisco",      "01_ios_basics"),
    ("cisco",      "02_vlans"),
    ("cisco",      "03_routing"),
    ("python",     "01_basics"),
    ("python",     "02_data_structures"),
    ("python",     "03_networking"),
    ("linux",      "01_commands"),
    ("linux",      "02_filesystem"),
    ("linux",      "03_networking"),
])
def test_lesson_page_ok(client, category, slug):
    response = client.get(f"/lesson/{category}/{slug}")
    assert response.status_code == 200


def test_lesson_page_shows_title(client):
    response = client.get("/lesson/networking/01_osi_model")
    assert b"OSI" in response.data


def test_lesson_invalid_slug_returns_404(client):
    response = client.get("/lesson/networking/does_not_exist")
    assert response.status_code == 404


def test_lesson_invalid_category_returns_404(client):
    response = client.get("/lesson/invalid/01_osi_model")
    assert response.status_code == 404


# ── Chat page ──────────────────────────────────────────────────────────────────

def test_chat_page_ok(client):
    response = client.get("/chat")
    assert response.status_code == 200


def test_chat_page_contains_input(client):
    response = client.get("/chat")
    assert b"chat-input" in response.data


# ── API /api/chat ──────────────────────────────────────────────────────────────

def test_api_chat_no_api_key_returns_fallback(client, monkeypatch):
    """Without an API key, the endpoint returns a helpful fallback message."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post(
        "/api/chat",
        json={"message": "What is an IP address?"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "reply" in data
    assert "OPENAI_API_KEY" in data["reply"]


def test_api_chat_missing_message(client):
    response = client.post("/api/chat", json={}, content_type="application/json")
    assert response.status_code == 400


def test_api_chat_empty_message(client):
    response = client.post(
        "/api/chat",
        json={"message": "   "},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_api_chat_no_json_body(client):
    response = client.post("/api/chat", data="not json", content_type="text/plain")
    assert response.status_code in (400, 415)
