import os
import json
import re
from html import unescape

import bleach
import markdown as md
import structlog
import yaml
from flask import Flask, render_template, request, jsonify, url_for, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import Markup
from prometheus_flask_exporter import PrometheusMetrics
import config
import ai_providers
import instructor_agent

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

logger = structlog.get_logger(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=[])
metrics = PrometheusMetrics(app)

MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "pymdownx.superfences",
    "tables",
    "nl2br",
    "codehilite",
    "attr_list",
]

BLEACH_ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p",
    "pre",
    "code",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "img",
    "div",
    "span",
    "br",
]
BLEACH_ALLOWED_ATTRS = {
    "*": ["class"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "class"],
}

MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


@app.context_processor
def inject_static_asset_url():
    """Provide a cache-busted static asset URL helper for templates."""
    def static_asset_url(filename):
        static_path = os.path.join(app.static_folder, filename)
        if os.path.isfile(static_path):
            version = int(os.path.getmtime(static_path))
            return url_for("static", filename=filename, v=version)
        return url_for("static", filename=filename)

    return {"static_asset_url": static_asset_url}

CATEGORIES = {
    "networking": {
        "title": "Networking",
        "icon": "🌐",
        "description": "Learn fundamental and advanced networking concepts including OSI model, TCP/IP, subnetting, and more.",
        "color": "blue",
    },
    "cisco": {
        "title": "Cisco",
        "icon": "🔧",
        "description": "Master Cisco IOS, VLANs, routing protocols, switching, and enterprise networking.",
        "color": "teal",
    },
    "python": {
        "title": "Python",
        "icon": "🐍",
        "description": "Learn Python programming from basics to advanced topics including network automation.",
        "color": "green",
    },
    "linux": {
        "title": "Linux",
        "icon": "🐧",
        "description": "Master Linux commands, file system management, shell scripting, and system administration.",
        "color": "orange",
    },
    "jetson": {
        "title": "Jetson AI",
        "icon": "🤖",
        "description": "Build practical edge AI workflows on NVIDIA Jetson Orin Nano 8GB: setup, media generation, and computer vision.",
        "color": "purple",
    },
}

# ---------------------------------------------------------------------------
# Jinja2 filter
# ---------------------------------------------------------------------------

@app.template_filter("markdown_to_html")
def markdown_to_html(text):
    """Convert a markdown string to safe HTML."""
    if not text:
        return ""

    mermaid_blocks = []

    def _capture_mermaid(match):
        idx = len(mermaid_blocks)
        mermaid_blocks.append(match.group(1).strip())
        return f"MERMAID_BLOCK_{idx}"

    processed_text = MERMAID_BLOCK_RE.sub(_capture_mermaid, text)
    rendered = md.markdown(
        processed_text,
        extensions=MARKDOWN_EXTENSIONS,
    )

    for idx, block in enumerate(mermaid_blocks):
        token = f"MERMAID_BLOCK_{idx}"
        diagram_html = f'<div class="mermaid">{block}</div>'
        rendered = rendered.replace(f"<p>{token}</p>", diagram_html)
        rendered = rendered.replace(token, diagram_html)

    rendered = bleach.clean(
        rendered,
        tags=BLEACH_ALLOWED_TAGS,
        attributes=BLEACH_ALLOWED_ATTRS,
        protocols=["http", "https", "mailto", "data"],
        strip=True,
    )

    # Bleach escapes Mermaid operators (like -->); restore only inside Mermaid blocks.
    rendered = re.sub(
        r'<div class="mermaid">(.*?)</div>',
        lambda m: f'<div class="mermaid">{unescape(m.group(1))}</div>',
        rendered,
        flags=re.DOTALL,
    )

    return Markup(
        rendered
    )


# ---------------------------------------------------------------------------
# Content helpers – lessons
# ---------------------------------------------------------------------------

def load_lessons(category):
    """Load all lessons for a given category from YAML files."""
    category_dir = os.path.join(config.CONTENT_DIR, category)
    lessons = []
    if not os.path.isdir(category_dir):
        return lessons
    for filename in sorted(os.listdir(category_dir)):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(category_dir, filename)
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    data["slug"] = filename.replace(".yaml", "").replace(".yml", "")
                    lessons.append(data)
    return lessons


def load_lesson(category, slug):
    """Load a single lesson by category and slug."""
    for ext in (".yaml", ".yml"):
        filepath = os.path.join(config.CONTENT_DIR, category, slug + ext)
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    data["slug"] = slug
                    return data
    return None


def build_fast_track_sections(category, lesson_title):
    """Generate extra advanced sections to lengthen lessons and increase pace."""
    common_sections = [
        {
            "heading": "Fast-Track Sprint (45 Minutes)",
            "content": f"""
Move quickly through **{lesson_title}** with this timed sprint:

1. **10 min**: Re-state the core concept in your own words and list 3 practical use-cases.
2. **15 min**: Build or run a minimal working demo that proves the concept end-to-end.
3. **10 min**: Add one failure test and one performance check.
4. **10 min**: Write a short technical debrief with tradeoffs and next improvements.

Pace rule:
- If you are blocked for more than 5 minutes, reduce scope and keep moving.
- Ship a working baseline first, then optimize.
""",
        },
        {
            "heading": "Challenge Ladder (Bronze to Gold)",
            "content": """
Use this challenge progression to deepen mastery quickly:

- **Bronze**: Reproduce baseline behavior from the lesson exactly.
- **Silver**: Add observability (logs, metrics, or validation checks).
- **Gold**: Improve speed, reliability, or clarity with a measurable result.

Score yourself after each rung:
- Correctness (0-5)
- Speed of delivery (0-5)
- Debugging quality (0-5)
- Communication quality (0-5)

Target: at least **15/20** before advancing.
""",
        },
    ]

    category_sections = {
        "linux": [
            {
                "heading": "Linux Deep Ops Drill",
                "content": """
Run this accelerated admin drill on a practice VM:

```bash
# 1) Create sandbox
mkdir -p ~/lab/{logs,data,bin} && cd ~/lab

# 2) Generate files and inspect metadata
for i in {1..5}; do echo "entry-$i" >> logs/app.log; done
ls -lah logs && stat logs/app.log

# 3) Search and filter quickly
grep -n "entry" logs/app.log | wc -l
find ~/lab -type f -name "*.log"

# 4) Permission hardening
chmod 640 logs/app.log
sudo chown "$USER":"$USER" logs/app.log
```

Deliverable:
- A short report listing commands used, why they were chosen, and one safer alternative.
""",
            },
            {
                "heading": "Incident Response Mini-Scenario",
                "content": """
Scenario: a service fails at startup after a config change.

Response sequence:
1. Verify process and port state.
2. Inspect latest logs and isolate first meaningful error.
3. Roll back the minimal change.
4. Validate service health and create a prevention checklist.

Focus on decision speed: you should produce a first diagnosis in under 8 minutes.
""",
            },
        ],
        "networking": [
            {
                "heading": "Packet Reasoning Lab",
                "content": """
Use fast packet-level reasoning for each concept in this lesson:

1. Identify source/destination addresses.
2. Identify encapsulation at each layer.
3. Predict next hop behavior.
4. Explain where the packet could fail and how to prove it.

Template:
```text
Flow:
Host A -> Switch -> Router -> ISP -> Service

Checks:
- L2: MAC table / VLAN membership
- L3: route lookup / gateway correctness
- L4: port reachability
```

Deliverable:
- One complete packet walk with a verified failure point and fix.
""",
            },
            {
                "heading": "Time-Boxed Subnet and Routing Set",
                "content": """
Complete 5 rapid problems in 20 minutes:

- 2 subnetting tasks with host-range validation
- 2 route selection tasks (longest-prefix match)
- 1 troubleshooting task with overlapping routes

Rule: show both the answer and the calculation path.
""",
            },
        ],
        "cisco": [
            {
                "heading": "Cisco CLI Speed Lab",
                "content": """
Practice high-frequency IOS workflow patterns:

```text
enable
configure terminal
interface g0/1
description Uplink-to-Core
switchport mode trunk
switchport trunk allowed vlan 10,20,30
end
write memory
show run interface g0/1
show interfaces trunk
```

Target outcomes:
- Correct syntax without tab-complete dependency
- Verification commands after every major change
- Rollback command prepared before risky edits
""",
            },
            {
                "heading": "Change Window Simulation",
                "content": """
Simulate a 30-minute production change window:

1. Pre-check (baseline state capture)
2. Change application (small, reversible steps)
3. Validation (control-plane + data-plane)
4. Backout trigger criteria
5. Post-change summary

This builds real-world speed with safe execution discipline.
""",
            },
        ],
        "python": [
            {
                "heading": "Python Performance and Reliability Pass",
                "content": """
Take a lesson script from working to production-grade:

1. Add type hints for core functions.
2. Add input validation and explicit exceptions.
3. Add structured logging for key transitions.
4. Add 3 focused tests: happy path, edge case, failure case.

Example scaffold:
```python
def parse_record(line: str) -> dict:
    if not line.strip():
        raise ValueError("empty line")
    # parse and validate fields
    return {"ok": True}
```

Measure improvement by reduced debug time and clearer failure messages.
""",
            },
            {
                "heading": "Automation Sprint",
                "content": """
Build a tiny automation utility in under 40 minutes:

- Input: file or API response
- Transform: parse, filter, normalize
- Output: human-readable report and machine-readable JSON

Stretch goal:
- Add retry logic and timeout handling for external calls.
""",
            },
        ],
        "jetson": [
            {
                "heading": "Edge Optimization Sprint",
                "content": """
Push the lesson artifact toward real deployment constraints:

1. Measure baseline latency and memory.
2. Reduce overhead (model warmup, pre-allocation, batch tuning).
3. Re-measure and document delta.

Benchmark template:
```text
Metric        Baseline   Optimized   Delta
Latency p95   120 ms     84 ms       -30%
RAM usage     2.1 GB     1.7 GB      -19%
```

Aim for one measurable improvement, not theoretical tuning.
""",
            },
            {
                "heading": "Deployment Readiness Checklist",
                "content": """
Before shipping on Jetson, confirm:

- Deterministic startup path
- Health endpoints and watchdog behavior
- Graceful degradation when GPU is unavailable
- Resource limits and thermal behavior under sustained load
- Reproducible setup instructions

Deliver a one-page readiness note with risks and mitigations.
""",
            },
        ],
    }

    return common_sections + category_sections.get(category, [])


# ---------------------------------------------------------------------------
# Content helpers – assignments
# ---------------------------------------------------------------------------

ASSIGNMENTS_DIR = os.path.join(os.path.dirname(__file__), "assignments")


def load_assignments(category):
    """Load all assignments for a given category from YAML files."""
    category_dir = os.path.join(ASSIGNMENTS_DIR, category)
    assignments = []
    if not os.path.isdir(category_dir):
        return assignments
    for filename in sorted(os.listdir(category_dir)):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(category_dir, filename)
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    data["slug"] = filename.replace(".yaml", "").replace(".yml", "")
                    assignments.append(data)
    return assignments


def load_assignment(category, slug):
    """Load a single assignment by category and slug."""
    for ext in (".yaml", ".yml"):
        filepath = os.path.join(ASSIGNMENTS_DIR, category, slug + ext)
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    data["slug"] = slug
                    return data
    return None


# ---------------------------------------------------------------------------
# Routes – lessons
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    category_data = {}
    for key, meta in CATEGORIES.items():
        lessons = load_lessons(key)
        category_data[key] = {**meta, "lesson_count": len(lessons)}
    return render_template("index.html", categories=category_data)


@app.route("/category/<category>")
def category(category):
    if category not in CATEGORIES:
        return render_template("404.html"), 404
    meta = CATEGORIES[category]
    lessons = load_lessons(category)
    return render_template("category.html", category=category, meta=meta, lessons=lessons)


@app.route("/lesson/<category>/<slug>")
def lesson(category, slug):
    if category not in CATEGORIES:
        return render_template("404.html"), 404
    data = load_lesson(category, slug)
    if not data:
        return render_template("404.html"), 404

    extra_sections = build_fast_track_sections(category, data.get("title", "Lesson"))
    data["sections"] = data.get("sections", []) + extra_sections

    # Pre-render section markdown to HTML to avoid template/filter variance.
    sections = data.get("sections", [])
    for section in sections:
        section["content_html"] = markdown_to_html(section.get("content", ""))
    meta = CATEGORIES[category]
    lessons = load_lessons(category)
    current_index = next((i for i, l in enumerate(lessons) if l["slug"] == slug), None)
    prev_lesson = lessons[current_index - 1] if current_index and current_index > 0 else None
    next_lesson = (
        lessons[current_index + 1]
        if current_index is not None and current_index < len(lessons) - 1
        else None
    )
    return render_template(
        "lesson.html",
        lesson=data,
        meta=meta,
        category=category,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
    )


# ---------------------------------------------------------------------------
# Routes – assignments
# ---------------------------------------------------------------------------

@app.route("/assignments")
def assignments_home():
    category_data = {}
    for key, meta in CATEGORIES.items():
        items = load_assignments(key)
        category_data[key] = {**meta, "assignment_count": len(items)}
    return render_template("assignments_home.html", categories=category_data)


@app.route("/assignments/<category>")
def assignments(category):
    if category not in CATEGORIES:
        return render_template("404.html"), 404
    meta = CATEGORIES[category]
    items = load_assignments(category)
    return render_template(
        "assignments.html", category=category, meta=meta, assignments=items
    )


@app.route("/assignment/<category>/<slug>")
def assignment(category, slug):
    if category not in CATEGORIES:
        return render_template("404.html"), 404
    data = load_assignment(category, slug)
    if not data:
        return render_template("404.html"), 404
    meta = CATEGORIES[category]
    all_assignments = load_assignments(category)
    current_index = next(
        (i for i, a in enumerate(all_assignments) if a["slug"] == slug), None
    )
    prev_assignment = (
        all_assignments[current_index - 1]
        if current_index and current_index > 0
        else None
    )
    next_assignment = (
        all_assignments[current_index + 1]
        if current_index is not None and current_index < len(all_assignments) - 1
        else None
    )
    return render_template(
        "assignment.html",
        assignment=data,
        meta=meta,
        category=category,
        prev_assignment=prev_assignment,
        next_assignment=next_assignment,
    )


# ---------------------------------------------------------------------------
# API – AI assistant
# ---------------------------------------------------------------------------

@app.route("/assistant")
def assistant():
    return render_template("assistant.html", categories=CATEGORIES)


@app.route("/instructor")
def instructor():
    return render_template("instructor.html", categories=CATEGORIES)


@app.route("/chat")
def chat():
    """Full-page AI chat interface (used by chat.js frontend)."""
    return render_template("chat.html", categories=CATEGORIES)


@app.route("/api/ask", methods=["POST"])
@limiter.limit("120/minute")
def ask():
    """AI assistant endpoint."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    if "message" not in data:
        return jsonify({"error": "Missing message field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    context = data.get("context", "general")
    provider = data.get("provider")

    system_prompt = ai_providers.EDUCATION_SYSTEM_PROMPT
    if context and context != "general":
        subject = CATEGORIES.get(context, {}).get("title", context)
        system_prompt += f" The current learning context is: {subject}."

    try:
        answer = ai_providers.ask(user_message, system_prompt=system_prompt, provider=provider)
        return jsonify({"answer": answer})
    except ai_providers.ProviderError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


@app.route("/api/chat", methods=["POST"])
@limiter.limit("120/minute")
def chat_api():
    """Chat API endpoint used by the chat.js frontend."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    if "message" not in data:
        return jsonify({"error": "Missing message field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Graceful fallback when no AI provider is configured
    if not ai_providers.get_available_providers():
        return jsonify(
            {
                "reply": (
                    "No AI provider is configured. Please set PERPLEXITY_API_KEY "
                    "(or OPENAI_API_KEY / GEMINI_API_KEY) in your .env file "
                    "to enable AI responses."
                )
            }
        ), 200

    category = data.get("category", "")
    provider = data.get("provider")
    settings = data.get("settings")

    system_prompt = ai_providers.EDUCATION_SYSTEM_PROMPT
    if category:
        subject = CATEGORIES.get(category.lower(), {}).get("title", category)
        system_prompt += f" The current learning context is: {subject}."

    try:
        payload = ai_providers.ask_chat(
            user_message,
            system_prompt=system_prompt,
            provider=provider,
            chat_options=settings,
        )
        return jsonify(payload)
    except ai_providers.ProviderError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.route("/api/chat/stream", methods=["POST"])
@limiter.limit("120/minute")
def chat_stream_api():
    """Streaming chat endpoint (SSE over POST)."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    if "message" not in data:
        return jsonify({"error": "Missing message field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    category = data.get("category", "")
    provider = data.get("provider")
    settings = data.get("settings")

    system_prompt = ai_providers.EDUCATION_SYSTEM_PROMPT
    if category:
        subject = CATEGORIES.get(category.lower(), {}).get("title", category)
        system_prompt += f" The current learning context is: {subject}."

    def generate():
        try:
            if not ai_providers.get_available_providers():
                fallback = (
                    "No AI provider is configured. Please set PERPLEXITY_API_KEY "
                    "(or OPENAI_API_KEY / GEMINI_API_KEY) in your .env file "
                    "to enable AI responses."
                )
                yield _sse("delta", {"text": fallback})
                yield _sse("done", {"reply": fallback, "provider": "none"})
                return

            for event in ai_providers.stream_chat(
                user_message,
                system_prompt=system_prompt,
                provider=provider,
                chat_options=settings,
            ):
                yield _sse(event.get("event", "delta"), event.get("data", {}))
        except ai_providers.ProviderError as exc:
            yield _sse("error", {"message": str(exc), "status": exc.status_code})
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": f"Unexpected server error: {exc}", "status": 500})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/instructor", methods=["POST"])
@limiter.limit("120/minute")
def instructor_api():
    """
    Instructor agent endpoint supporting multi-turn conversations.

    Expected JSON body:
    {
        "messages": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "..."}
        ],
        "subject": "Linux",   // optional
        "provider": "openai"  // optional
    }

    Returns:
    {
        "reply": "..."
    }
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    messages = data.get("messages")
    if not messages or not isinstance(messages, list):
        return jsonify({"error": "Missing or invalid messages field"}), 400

    for msg in messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            return jsonify({"error": "Each message must have 'role' and 'content' fields"}), 400
        if msg["role"] not in ("user", "assistant"):
            return jsonify({"error": "Message role must be 'user' or 'assistant'"}), 400
        if not isinstance(msg["content"], str):
            return jsonify({"error": "Message content must be a string"}), 400

    if messages[-1]["role"] != "user":
        return jsonify({"error": "Last message must be from the user"}), 400

    last_content = messages[-1]["content"].strip()
    if not last_content:
        return jsonify({"error": "Last message content cannot be empty"}), 400

    if not ai_providers.get_available_providers():
        return jsonify(
            {
                "reply": (
                    "No AI provider is configured. Please set PERPLEXITY_API_KEY "
                    "(or OPENAI_API_KEY / GEMINI_API_KEY) in your .env file "
                    "to enable the instructor agent."
                )
            }
        ), 200

    subject = data.get("subject", "")
    provider = data.get("provider")
    if provider is not None and provider not in ai_providers.PROVIDER_LABELS:
        return jsonify({"error": f"Invalid provider. Choose from: {', '.join(ai_providers.PROVIDER_LABELS)}"}), 400

    try:
        reply = instructor_agent.ask(messages, subject=subject or None, provider=provider)
        return jsonify({"reply": reply})
    except ai_providers.ProviderError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500


# ---------------------------------------------------------------------------
# API – assignment grading
# ---------------------------------------------------------------------------

@app.route("/api/grade", methods=["POST"])
@limiter.limit("60/minute")
def grade():
    """
    Grade an assignment submission.

    Expected JSON body:
    {
        "category": "networking",
        "slug": "01_osi_model_assignment",
        "answers": {
            "1": "user answer or selected option index as string",
            "2": "free-text answer",
            ...
        }
    }

    Returns:
    {
        "score": 70,
        "max_score": 100,
        "percentage": 70.0,
        "letter_grade": "C",
        "tasks": [
            {
                "id": 1,
                "type": "multiple_choice",
                "score": 10,
                "max_score": 10,
                "correct": true,
                "feedback": "Correct! ...",
                "ideal_answer": "..."
            },
            ...
        ],
        "overall_feedback": "..."
    }
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "Missing request body"}), 400

    category = body.get("category", "")
    slug = body.get("slug", "")
    answers = body.get("answers", {})

    if not category or not slug:
        return jsonify({"error": "Missing category or slug"}), 400

    assignment_data = load_assignment(category, slug)
    if not assignment_data:
        return jsonify({"error": "Assignment not found"}), 404

    tasks = assignment_data.get("tasks", [])
    graded_tasks = []
    total_score = 0
    total_max = 0

    open_tasks_to_grade = []  # collected for batch AI grading

    for task in tasks:
        task_id = str(task["id"])
        task_type = task.get("type", "short_answer")
        max_pts = task.get("points", 10)
        user_answer = answers.get(task_id, "").strip()

        total_max += max_pts

        if task_type == "multiple_choice":
            result = _grade_multiple_choice(task, user_answer, max_pts)
            total_score += result["score"]
            graded_tasks.append(result)
        else:
            # Defer open-ended tasks to AI grading
            open_tasks_to_grade.append((task, user_answer, max_pts))

    # AI-grade all open-ended tasks (requires API key)
    if open_tasks_to_grade:
        if not ai_providers.get_available_providers():
            # Graceful degradation: return pending results without AI score
            for task, user_answer, max_pts in open_tasks_to_grade:
                graded_tasks.append(
                    {
                        "id": task["id"],
                        "type": task.get("type"),
                        "score": 0,
                        "max_score": max_pts,
                        "correct": False,
                        "feedback": "AI grading is unavailable (no API key configured). Please review the ideal answer below.",
                        "ideal_answer": task.get("sample_answer", "See rubric."),
                        "pending": True,
                    }
                )
        else:
            subject = CATEGORIES.get(category, {}).get("title", category)
            for task, user_answer, max_pts in open_tasks_to_grade:
                try:
                    result = ai_providers.grade_open_ended(task, user_answer, max_pts, subject)
                    total_score += result["score"]
                    graded_tasks.append(result)
                except ai_providers.ProviderError as exc:
                    return jsonify({"error": str(exc)}), exc.status_code

    # Sort graded tasks by original task id order
    id_order = {str(t["id"]): i for i, t in enumerate(tasks)}
    graded_tasks.sort(key=lambda t: id_order.get(str(t["id"]), 999))

    percentage = round((total_score / total_max) * 100, 1) if total_max else 0
    letter_grade = _letter_grade(percentage)

    overall_feedback = _overall_feedback(percentage, graded_tasks)

    return jsonify(
        {
            "score": total_score,
            "max_score": total_max,
            "percentage": percentage,
            "letter_grade": letter_grade,
            "tasks": graded_tasks,
            "overall_feedback": overall_feedback,
        }
    )


def _grade_multiple_choice(task, user_answer, max_pts):
    """Grade a multiple-choice task locally (no AI needed)."""
    try:
        selected = int(user_answer)
    except (ValueError, TypeError):
        selected = -1

    correct_index = task.get("answer", -1)
    is_correct = selected == correct_index
    score = max_pts if is_correct else 0
    options = task.get("options", [])
    correct_text = options[correct_index] if 0 <= correct_index < len(options) else "N/A"

    return {
        "id": task["id"],
        "type": "multiple_choice",
        "score": score,
        "max_score": max_pts,
        "correct": is_correct,
        "feedback": (
            "✅ Correct! " + task.get("explanation", "")
            if is_correct
            else "❌ Incorrect. " + task.get("explanation", "")
        ),
        "ideal_answer": correct_text,
    }


def _letter_grade(percentage):
    if percentage >= 90:
        return "A"
    if percentage >= 80:
        return "B"
    if percentage >= 70:
        return "C"
    if percentage >= 60:
        return "D"
    return "F"


def _overall_feedback(percentage, graded_tasks):
    missed = [t for t in graded_tasks if not t.get("correct")]
    if percentage >= 90:
        return "Excellent work! You have a strong grasp of this material."
    if percentage >= 70:
        missed_str = ", ".join(str(t["id"]) for t in missed)
        return f"Good effort! Review the feedback on task(s) {missed_str} to strengthen your understanding."
    return (
        "Keep practicing! Review the lesson material and the ideal answers below, "
        "then try again once you feel more confident."
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=config.DEBUG, host="0.0.0.0", port=5000)
