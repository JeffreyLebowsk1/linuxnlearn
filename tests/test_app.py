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
    ("python",     "01_python_basics"),
    ("python",     "02_data_structures"),
    ("python",     "03_networking"),
    ("linux",      "01_essential_commands"),
    ("linux",      "02_filesystem"),
    ("linux",      "03_networking"),
])
def test_lesson_page_ok(client, category, slug):
    response = client.get(f"/lesson/{category}/{slug}")
    assert response.status_code == 200


def test_lesson_page_shows_title(client):
    response = client.get("/lesson/networking/01_osi_model")
    assert b"OSI" in response.data


def test_lesson_markdown_renders_as_html(client):
    response = client.get("/lesson/python/02_network_automation")
    assert response.status_code == 200
    assert b"&lt;p&gt;" not in response.data
    assert (
        b"<pre><code" in response.data
        or b"codehilite" in response.data
        or b"class=\"highlight\"" in response.data
    )


def test_osi_lesson_paragraphs_are_not_escaped(client):
    response = client.get("/lesson/networking/01_osi_model")
    assert response.status_code == 200
    assert b"&lt;p&gt;In the early 1970s" not in response.data
    assert b"<p>In the early 1970s" in response.data


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
    import ai_providers

    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setattr(ai_providers, "get_available_providers", lambda: [])
    response = client.post(
        "/api/chat",
        json={"message": "What is an IP address?"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "reply" in data
    assert "PERPLEXITY_API_KEY" in data["reply"]


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


def test_api_chat_stream_no_api_key_returns_fallback_events(client, monkeypatch):
    import ai_providers

    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setattr(ai_providers, "get_available_providers", lambda: [])

    response = client.post(
        "/api/chat/stream",
        json={"message": "What is an IP address?"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.data.decode()
    assert "event: delta" in data
    assert "event: done" in data
    assert "PERPLEXITY_API_KEY" in data


def test_api_chat_stream_missing_message(client):
    response = client.post("/api/chat/stream", json={}, content_type="application/json")
    assert response.status_code == 400


# ── Instructor page ────────────────────────────────────────────────────────────

def test_instructor_page_ok(client):
    response = client.get("/instructor")
    assert response.status_code == 200


def test_instructor_page_contains_chat_input(client):
    response = client.get("/instructor")
    assert b"chat-input" in response.data


def test_instructor_page_contains_heading(client):
    response = client.get("/instructor")
    assert b"Instructor" in response.data


# ── API /api/instructor ────────────────────────────────────────────────────────

def test_api_instructor_no_api_key_returns_fallback(client, monkeypatch):
    """Without an API key, the endpoint returns a helpful fallback message."""
    import ai_providers

    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setattr(ai_providers, "get_available_providers", lambda: [])
    response = client.post(
        "/api/instructor",
        json={"messages": [{"role": "user", "content": "Teach me about Linux"}]},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "reply" in data
    assert "PERPLEXITY_API_KEY" in data["reply"]


def test_api_instructor_missing_messages(client):
    response = client.post("/api/instructor", json={}, content_type="application/json")
    assert response.status_code == 400


def test_api_instructor_empty_messages_list(client):
    response = client.post(
        "/api/instructor",
        json={"messages": []},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_api_instructor_invalid_role(client):
    response = client.post(
        "/api/instructor",
        json={"messages": [{"role": "system", "content": "Hello"}]},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_api_instructor_last_message_not_user(client):
    response = client.post(
        "/api/instructor",
        json={"messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_api_instructor_empty_last_message(client):
    response = client.post(
        "/api/instructor",
        json={"messages": [{"role": "user", "content": "   "}]},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_api_instructor_no_json_body(client):
    response = client.post("/api/instructor", data="not json", content_type="text/plain")
    assert response.status_code in (400, 415)


def test_api_instructor_missing_content_field(client):
    response = client.post(
        "/api/instructor",
        json={"messages": [{"role": "user"}]},
        content_type="application/json",
    )
    assert response.status_code == 400


# ── instructor_agent unit tests ────────────────────────────────────────────────

def test_instructor_ask_raises_on_empty_messages():
    import instructor_agent
    import pytest
    with pytest.raises(ValueError):
        instructor_agent.ask([])


def test_instructor_ask_with_subject(monkeypatch):
    import instructor_agent
    import ai_providers

    captured = {}

    def mock_ask_with_history(messages, system_prompt=None, provider=None):
        captured["system_prompt"] = system_prompt
        captured["messages"] = messages
        return "Mock reply"

    monkeypatch.setattr(ai_providers, "ask_with_history", mock_ask_with_history)

    result = instructor_agent.ask(
        [{"role": "user", "content": "Hello"}],
        subject="Linux",
    )
    assert result == "Mock reply"
    assert "Linux" in captured["system_prompt"]
    assert captured["messages"] == [{"role": "user", "content": "Hello"}]


def test_instructor_ask_without_subject(monkeypatch):
    import instructor_agent
    import ai_providers

    captured = {}

    def mock_ask_with_history(messages, system_prompt=None, provider=None):
        captured["system_prompt"] = system_prompt
        return "Mock reply"

    monkeypatch.setattr(ai_providers, "ask_with_history", mock_ask_with_history)

    instructor_agent.ask([{"role": "user", "content": "Hello"}])
    assert "studying" not in captured["system_prompt"]
    assert "instructor" in captured["system_prompt"].lower()
