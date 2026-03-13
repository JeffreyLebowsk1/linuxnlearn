# LinuxNLearn

An AI-assisted IT education web application built with Flask. Covers Linux, Networking, Cisco, and Python through structured lessons with an integrated AI chat assistant.

## Features

- **Four learning categories**: Linux, Networking, Cisco, Python
- **YAML-based lessons** — easy to add new content without touching code
- **AI Chat Assistant** — powered by OpenAI GPT, available globally and per-lesson
- **Clean, responsive UI** — works on desktop and mobile

## Quick Start

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
# Edit .env and add your OPENAI_API_KEY

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

The AI chat feature requires an OpenAI API key. Without it, users see a friendly message explaining how to enable it. Set `OPENAI_API_KEY` in your `.env` file to activate the assistant.

## Running Tests

```bash
pytest tests/ -v
```
