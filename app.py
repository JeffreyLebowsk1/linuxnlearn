import json
import os

import markdown as md
import openai
import yaml
from flask import Flask, render_template, request, jsonify
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

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
}

# ---------------------------------------------------------------------------
# Jinja2 filter
# ---------------------------------------------------------------------------

@app.template_filter("markdown_to_html")
def markdown_to_html(text):
    """Convert a markdown string to safe HTML."""
    if not text:
        return ""
    return md.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
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


@app.route("/api/ask", methods=["POST"])
def ask():
    """AI assistant endpoint."""
    if not config.OPENAI_API_KEY:
        return (
            jsonify(
                {
                    "error": "OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file."
                }
            ),
            503,
        )

    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing message field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    context = data.get("context", "general")

    system_prompt = (
        "You are an expert IT educator specializing in networking, Cisco technologies, "
        "Python programming, and Linux administration. Your goal is to teach clearly and "
        "progressively, using examples and analogies to make complex concepts accessible. "
        "When explaining networking concepts, relate them to real-world scenarios. "
        "When explaining Cisco IOS commands, always show the syntax and give practical examples. "
        "When teaching Python, provide runnable code snippets. "
        "When explaining Linux, include actual commands the user can try. "
        "Keep responses concise but thorough, and always encourage further exploration."
    )
    if context and context != "general":
        subject = CATEGORIES.get(context, {}).get("title", context)
        system_prompt += f" The current learning context is: {subject}."

    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        answer = response.choices[0].message.content
        return jsonify({"answer": answer})
    except openai.AuthenticationError:
        return jsonify({"error": "Invalid OpenAI API key. Please check your configuration."}), 401
    except openai.RateLimitError:
        return jsonify({"error": "Rate limit exceeded. Please try again in a moment."}), 429
    except openai.OpenAIError as e:
        return jsonify({"error": f"AI service error: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# API – assignment grading
# ---------------------------------------------------------------------------

@app.route("/api/grade", methods=["POST"])
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
        if not config.OPENAI_API_KEY:
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
            try:
                client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
                for task, user_answer, max_pts in open_tasks_to_grade:
                    result = _grade_open_ended_ai(client, task, user_answer, max_pts, category)
                    total_score += result["score"]
                    graded_tasks.append(result)
            except openai.OpenAIError as e:
                return jsonify({"error": f"AI grading error: {str(e)}"}), 500

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


def _grade_open_ended_ai(client, task, user_answer, max_pts, category):
    """Ask the AI to grade an open-ended or practical task."""
    subject = CATEGORIES.get(category, {}).get("title", category)
    question = task.get("question", "")
    rubric = task.get("rubric", "")
    sample_answer = task.get("sample_answer", "")

    if not user_answer:
        return {
            "id": task["id"],
            "type": task.get("type"),
            "score": 0,
            "max_score": max_pts,
            "correct": False,
            "feedback": "No answer provided.",
            "ideal_answer": sample_answer or "See rubric.",
        }

    prompt = (
        f"You are grading a student assignment on {subject}.\n\n"
        f"Question ({max_pts} points):\n{question}\n\n"
        f"Grading rubric:\n{rubric}\n\n"
        f"Student's answer:\n{user_answer}\n\n"
        f"Evaluate the answer strictly according to the rubric. "
        f"Respond with a JSON object using exactly these keys:\n"
        f'{{"score": <integer 0 to {max_pts}>, '
        f'"correct": <true if score >= {round(max_pts * 0.7)}>, '
        f'"feedback": "<specific, constructive feedback on what was right and what was missing>", '
        f'"ideal_answer": "<a concise model answer>"}}'
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=512,
        temperature=0.3,
    )

    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

    score = max(0, min(max_pts, int(data.get("score", 0))))
    return {
        "id": task["id"],
        "type": task.get("type"),
        "score": score,
        "max_score": max_pts,
        "correct": bool(data.get("correct", score >= round(max_pts * 0.7))),
        "feedback": data.get("feedback", "No feedback available."),
        "ideal_answer": data.get("ideal_answer", sample_answer or "See rubric."),
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
