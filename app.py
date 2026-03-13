import os
import yaml
from flask import Flask, render_template, request, jsonify
import openai
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
    next_lesson = lessons[current_index + 1] if current_index is not None and current_index < len(lessons) - 1 else None
    return render_template(
        "lesson.html",
        lesson=data,
        meta=meta,
        category=category,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
    )


@app.route("/assistant")
def assistant():
    return render_template("assistant.html", categories=CATEGORIES)


@app.route("/api/ask", methods=["POST"])
def ask():
    """AI assistant endpoint."""
    if not config.OPENAI_API_KEY:
        return jsonify({"error": "OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file."}), 503

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


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=config.DEBUG, host="0.0.0.0", port=5000)
