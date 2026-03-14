# LinuxNLearn

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/JeffreyLebowsk1/linuxnlearn)

An AI-assisted IT education web application built with Flask. Covers Linux, Networking, Cisco, and Python through structured lessons with an integrated AI chat assistant.

## Features

- **Four learning categories**: Linux, Networking, Cisco, Python
- **YAML-based lessons** — easy to add new content without touching code
- **AI Chat Assistant** — powered by Perplexity Sonar (with OpenAI and Google Gemini also supported), available globally and per-lesson
- **Clean, responsive UI** — works on desktop and mobile

## Run in the Cloud — No Local Setup Needed

### GitHub Codespaces (Recommended)

The fastest way to get started. GitHub Codespaces runs a full development environment in your browser — no installation required.

**Free tier:** 60 hours/month (GitHub Free) · 120 hours/month (GitHub Pro)

1. Click the **Open in GitHub Codespaces** badge above, or go to **Code → Codespaces → Create codespace on main**.
2. Wait ~1 minute for the environment to build. Dependencies are installed automatically.
3. Open the `.env` file (created for you from `.env.example`) and add your AI provider key:
   ```
   PERPLEXITY_API_KEY=your_key_here
   ```
   > **Tip — use Codespaces Secrets instead of `.env`:** In your GitHub account go to **Settings → Codespaces → Secrets** and add `PERPLEXITY_API_KEY` (or `OPENAI_API_KEY` / `GEMINI_API_KEY`). It will be injected automatically into every Codespace you open for this repo, so you never have to edit `.env` manually.
4. In the terminal, run the app:
   ```bash
   python run.py
   ```
5. A browser tab opens automatically with the live app. The URL (e.g. `https://<name>-5000.app.github.dev`) is publicly accessible and can be shared.

## Quick Start (Local)

```bash
# 1. Clone and enter the repo
git clone https://github.com/JeffreyLebowsk1/linuxnlearn.git
cd linuxnlearn

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your PERPLEXITY_API_KEY

# 5. Run the app
python app.py
# Open http://localhost:5000
```

## Project Structure

```
linuxnlearn/
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables
├── content/                # YAML lesson files
│   ├── networking/         # OSI model, TCP/IP, subnetting
│   ├── cisco/              # IOS basics, VLANs, routing
│   ├── python/             # Basics, data structures, networking
│   └── linux/              # Commands, filesystem, networking tools
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── category.html
│   ├── lesson.html
│   └── chat.html
├── static/
│   ├── css/style.css
│   └── js/
│       ├── main.js
│       └── chat.js
└── tests/
    └── test_app.py
```

## Adding New Lessons

Create a YAML file in `content/<category>/` following this structure:

```yaml
title: "Your Lesson Title"
description: "A short description."
sections:
  - heading: "Section Heading"
    text: "Paragraph text."
    points:
      - "Bullet point one"
      - "Bullet point two"
    code: |
      # Code block
      print("Hello!")
    table:
      headers: ["Col 1", "Col 2"]
      rows:
        - ["Row 1 A", "Row 1 B"]
key_takeaways:
  - "Key point 1"
  - "Key point 2"
```

## AI Chat

The AI chat feature requires a Perplexity API key (default provider). Without it, users see a friendly message explaining how to enable it. Set `PERPLEXITY_API_KEY` in your `.env` file to activate the assistant. OpenAI (`OPENAI_API_KEY`) and Google Gemini (`GEMINI_API_KEY`) are also supported — set `AI_PROVIDER=openai` or `AI_PROVIDER=gemini` in `.env` to use them instead.

## Running Tests

```bash
pytest tests/ -v
```

## Free Hosting (No Local Setup Required)

See the [GitHub Codespaces](#run-in-the-cloud--no-local-setup-needed) section above for the easiest option. Additional alternatives are listed below.

### Render.com (Free Web Service)

Render's free tier hosts the app publicly with zero DevOps required.

1. Fork this repository.
2. Go to [render.com](https://render.com) and create a free account.
3. Click **New → Blueprint** and connect your forked repository.  
   Render will detect `render.yaml` and configure the service automatically.
4. Set your AI provider key (`PERPLEXITY_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`) in the Render dashboard under **Environment**.
5. Click **Deploy** — your app will be live at a `*.onrender.com` URL.

> **Note:** Free Render services spin down after 15 minutes of inactivity and take a few seconds to wake up on the next request.

### Docker (Self-Hosted or Any Container Platform)

A `Dockerfile` is included for building a production-ready container image.

```bash
docker build -t linuxnlearn .
docker run -p 5000:5000 \
  -e PERPLEXITY_API_KEY=your_key_here \
  linuxnlearn
# Open http://localhost:5000
```

Deploy the image to any free container platform such as [Fly.io](https://fly.io) (free tier) or [Railway](https://railway.app) ($5/month free credit).
