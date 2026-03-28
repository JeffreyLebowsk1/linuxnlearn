# LinuxNLearn

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/JeffreyLebowsk1/linuxnlearn)

An AI-assisted IT education web application built with Flask. Provides **five accredited, college-level courses** in Linux, Networking, Cisco, Python, and Edge AI through structured lessons with an integrated AI chat assistant.

## Degree Pathway

All courses carry official course numbers, credit hours, department assignments, prerequisites, catalog descriptions, required textbooks, and faculty credential notes — matching the structure of accredited university programs. Completing the full sequence satisfies the core requirements of a systems/network engineering or AI/robotics degree track.

| Step | Course | Number | Credits | Department |
|------|--------|--------|---------|------------|
| 1 | Linux System Administration | SYS 202 | 3 + 1 lab | Systems Administration & Cybersecurity |
| 2 | Networking Fundamentals | NET 201 | 3 + 1 lab | Computer Science & Network Engineering |
| 3a *(parallel)* | Enterprise Networking (Cisco) | NET 310 | 3 + 2 lab | Computer Science & Network Engineering |
| 3b *(parallel)* | Python Programming | CS 215 | 3 + 1 lab | Computer Science & Software Engineering |
| 4 | Edge AI Development (Jetson) | AI 340 | 3 + 2 lab | Artificial Intelligence & Robotics |

### Prerequisites

```
CS 101 (Intro to Computing)  +  MATH 110 (College Mathematics)
              ↓
         SYS 202 Linux
              ↓
         NET 201 Networking
         ┌────┴────┐
         ↓         ↓
      NET 310    CS 215
      (Cisco)   (Python)
         ↓         ↓
         └────┬────┘
              ↓
          AI 340 Jetson AI
```

Each course page displays the full official syllabus including prerequisites, catalog description, assigned textbooks (with ISBN), and faculty credentials.

## Features

- **Five college-level courses**: Linux (SYS 202), Networking (NET 201), Cisco (NET 310), Python (CS 215), Edge AI (AI 340)
- **Full course syllabi** — course numbers, credit hours, department, prerequisites, catalog descriptions, required textbooks, and faculty notes
- **Degree pathway roadmap** — sequenced curriculum from Linux foundations to Edge AI deployment
- **YAML-based lessons** — easy to add new content without touching code
- **AI Chat Assistant** — powered by Perplexity Sonar (with OpenAI and Google Gemini also supported), available globally and per-lesson
- **Interactive labs** — simulated Linux terminal, subnet calculator, chmod calculator, Python sandbox, and Cisco IOS simulator
- **AI-graded assignments** — open-ended lab reports graded by AI with per-task feedback and letter grades
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
├── app.py                  # Flask application (course metadata, routes)
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables
├── content/                # YAML lesson files
│   ├── linux/              # SYS 202 — commands, filesystem, networking tools
│   ├── networking/         # NET 201 — OSI model, TCP/IP, subnetting
│   ├── cisco/              # NET 310 — IOS basics, VLANs, routing
│   ├── python/             # CS 215 — basics, data structures, automation
│   └── jetson/             # AI 340 — edge AI, TensorRT, computer vision
├── assignments/            # YAML graded assignment files (per course)
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html          # Home page with degree pathway roadmap
│   ├── learning_path.html  # Full degree path with syllabi
│   ├── category.html       # Category/course page (shows official syllabus card)
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
order: 1
summary: "Short summary shown in course catalog and lesson list."
learning_objectives:
  - "Students will be able to..."
  - "Students will understand..."
builds_on:
  - "Prior knowledge requirement"
sections:
  - heading: "Section Heading"
    content: |
      # Markdown content here
      Supports **bold**, `code`, tables, and code blocks.
quiz:
  - question: "Question text?"
    options: ["Option A", "Option B", "Option C", "Option D"]
    answer: 0      # index of correct option
    explanation: "Detailed explanation shown after answering."
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
