import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# ── Flask ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
PORT = int(os.environ.get("PORT", "5000"))

# ── Content paths ────────────────────────────────────────────────────────────
CONTENT_DIR = os.path.join(os.path.dirname(__file__), "content")

# ── AI providers ─────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")

# Which provider to use by default: "openai" | "gemini" | "perplexity"
AI_PROVIDER = os.environ.get("AI_PROVIDER", "perplexity").lower()

# ── ngrok ────────────────────────────────────────────────────────────────────
# Accept common authtoken variable names. Do not treat API keys as auth tokens.
NGROK_AUTH_TOKEN = (
	os.environ.get("NGROK_AUTH_TOKEN")
	or os.environ.get("NGROK_AUTHTOKEN")
	or ""
).strip().strip('"').strip("'")
NGROK_API_KEY = (os.environ.get("NGROK_API_KEY") or "").strip().strip('"').strip("'")
NGROK_DOMAIN = os.environ.get("NGROK_DOMAIN", "")   # optional static domain
