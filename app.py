import os
import secrets
import yaml
from flask import Flask, render_template, request, jsonify, abort
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    _secret_key = secrets.token_hex(32)
app.secret_key = _secret_key

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "content")

CATEGORIES = {
    "networking": {
        "title": "Networking",
        "description": "Learn OSI model, TCP/IP, subnetting, and more.",
        "icon": "🌐",
        "color": "blue",
    },
    "cisco": {
        "title": "Cisco",
        "description": "Master Cisco IOS, VLANs, routing protocols, and more.",
        "icon": "🔧",
        "color": "teal",
    },
    "python": {
        "title": "Python",
        "description": "Python basics, data structures, and network programming.",
        "icon": "🐍",
        "color": "green",
    },
    "linux": {
        "title": "Linux",
        "description": "Linux commands, file system, and networking tools.",
        "icon": "🐧",
        "color": "orange",
    },
}


def load_lessons(category):
    """Load all lessons for a given category from YAML files."""
    category_dir = os.path.join(CONTENT_DIR, category)
    lessons = []
    if not os.path.isdir(category_dir):
        return lessons
    for filename in sorted(os.listdir(category_dir)):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(category_dir, filename)
            with open(filepath, "r") as f:
                lesson = yaml.safe_load(f)
                if lesson:
                    lesson["slug"] = os.path.splitext(filename)[0]
                    lessons.append(lesson)
    return lessons


def load_lesson(category, slug):
    """Load a single lesson by category and slug."""
    for ext in (".yaml", ".yml"):
        filepath = os.path.join(CONTENT_DIR, category, slug + ext)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                lesson = yaml.safe_load(f)
                if lesson:
                    lesson["slug"] = slug
                    return lesson
    return None


@app.context_processor
def inject_categories():
    return {"categories": CATEGORIES}


@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORIES)


@app.route("/category/<category>")
def category(category):
    if category not in CATEGORIES:
        abort(404)
    cat_info = CATEGORIES[category]
    lessons = load_lessons(category)
    return render_template("category.html", category=category, cat_info=cat_info, lessons=lessons)


@app.route("/lesson/<category>/<slug>")
def lesson(category, slug):
    if category not in CATEGORIES:
        abort(404)
    lesson_data = load_lesson(category, slug)
    if lesson_data is None:
        abort(404)
    cat_info = CATEGORIES[category]
    return render_template("lesson.html", category=category, cat_info=cat_info, lesson=lesson_data)


@app.route("/chat")
def chat():
    return render_template("chat.html", categories=CATEGORIES)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    category_context = data.get("category", "")
    lesson_context = data.get("lesson", "")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return jsonify({
            "reply": (
                "The AI assistant requires an OpenAI API key. "
                "Please set the OPENAI_API_KEY environment variable to enable this feature."
            )
        })

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        system_prompt = (
            "You are a helpful assistant specializing in IT education, "
            "covering Linux, networking, Cisco technologies, and Python programming. "
            "Provide clear, concise, and accurate answers suitable for learners at all levels."
        )
        if category_context:
            system_prompt += f" The user is currently studying: {category_context}."
        if lesson_context:
            system_prompt += f" The current lesson is: {lesson_context}."

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=800,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": f"AI service error: {str(e)}"}), 500


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)
