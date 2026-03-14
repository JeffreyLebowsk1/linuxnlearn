"""
AI provider abstraction layer for LinuxNLearn.

Supported providers
-------------------
  openai      – OpenAI GPT-4o-mini (chat.completions)
  gemini      – Google Gemini 2.0 Flash (google-generativeai)
  perplexity  – Perplexity Sonar (OpenAI-compatible endpoint)

The active provider is chosen by:
  1. The ``provider`` argument passed to ask() / grade_open_ended()
  2. config.AI_PROVIDER  (set AI_PROVIDER= in .env)
  3. First provider whose API key is configured
"""

import json

import config

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

PROVIDER_LABELS = {
    "openai": "OpenAI (GPT-4o-mini)",
    "gemini": "Google Gemini 2.0 Flash",
    "perplexity": "Perplexity Sonar",
}

EDUCATION_SYSTEM_PROMPT = (
    "You are an expert IT educator specializing in networking, Cisco technologies, "
    "Python programming, and Linux administration. Your goal is to teach clearly and "
    "progressively, using examples and analogies to make complex concepts accessible. "
    "When explaining networking concepts, relate them to real-world scenarios. "
    "When explaining Cisco IOS commands, always show the syntax and give practical examples. "
    "When teaching Python, provide runnable code snippets. "
    "When explaining Linux, include actual commands the user can try. "
    "Keep responses concise but thorough, and always encourage further exploration."
)


class ProviderError(Exception):
    """Raised when an AI provider call fails."""

    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.status_code = status_code


def get_available_providers():
    """Return a list of provider names whose API keys are configured."""
    available = []
    if config.OPENAI_API_KEY:
        available.append("openai")
    if config.GEMINI_API_KEY:
        available.append("gemini")
    if config.PERPLEXITY_API_KEY:
        available.append("perplexity")
    return available


def resolve_provider(requested=None):
    """
    Determine which provider to use.

    Priority: explicitly requested → config default → first with a key → 'openai'
    (openai will fail gracefully with a "no key" message if not configured).
    """
    valid = set(PROVIDER_LABELS)
    if requested and requested in valid:
        return requested
    if config.AI_PROVIDER in valid:
        return config.AI_PROVIDER
    available = get_available_providers()
    return available[0] if available else "perplexity"


def ask(message, system_prompt=None, provider=None):
    """
    Send a chat message to the selected AI provider.

    Parameters
    ----------
    message : str
    system_prompt : str | None  – defaults to EDUCATION_SYSTEM_PROMPT
    provider : str | None       – "openai" | "gemini" | "perplexity" | None

    Returns
    -------
    str  – the model's reply text

    Raises
    ------
    ProviderError
    """
    if system_prompt is None:
        system_prompt = EDUCATION_SYSTEM_PROMPT
    provider = resolve_provider(provider)
    if provider == "gemini":
        return _ask_gemini(message, system_prompt)
    if provider == "perplexity":
        return _ask_perplexity(message, system_prompt)
    return _ask_openai(message, system_prompt)


def ask_with_history(messages, system_prompt=None, provider=None):
    """
    Send a multi-turn conversation to the selected AI provider.

    Parameters
    ----------
    messages : list[dict]
        Conversation history: [{"role": "user"|"assistant", "content": "..."}].
        The last entry must have role "user".
    system_prompt : str | None  – defaults to EDUCATION_SYSTEM_PROMPT
    provider : str | None       – "openai" | "gemini" | "perplexity" | None

    Returns
    -------
    str  – the model's reply text

    Raises
    ------
    ProviderError
    """
    if system_prompt is None:
        system_prompt = EDUCATION_SYSTEM_PROMPT
    provider = resolve_provider(provider)
    if provider == "gemini":
        return _ask_gemini_with_history(messages, system_prompt)
    if provider == "perplexity":
        return _ask_perplexity_with_history(messages, system_prompt)
    return _ask_openai_with_history(messages, system_prompt)


def grade_open_ended(task, user_answer, max_pts, subject, provider=None):
    """
    Grade an open-ended assignment task with AI.

    Returns a dict with keys:
      id, type, score, max_score, correct, feedback, ideal_answer
    """
    provider = resolve_provider(provider)
    if provider == "gemini":
        return _grade_gemini(task, user_answer, max_pts, subject)
    if provider == "perplexity":
        return _grade_perplexity(task, user_answer, max_pts, subject)
    return _grade_openai(task, user_answer, max_pts, subject)


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

_OPENAI_CHAT_MODEL = "gpt-4o-mini"


def _ask_openai(message, system_prompt):
    import openai

    if not config.OPENAI_API_KEY:
        raise ProviderError(
            "OpenAI API key not configured. Set OPENAI_API_KEY in your .env file.", 503
        )
    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=_OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except openai.AuthenticationError:
        raise ProviderError("Invalid OpenAI API key.", 401)
    except openai.RateLimitError:
        raise ProviderError("OpenAI rate limit exceeded. Try again in a moment.", 429)
    except openai.OpenAIError as exc:
        raise ProviderError(f"OpenAI error: {exc}", 500)


def _ask_openai_with_history(messages, system_prompt):
    import openai

    if not config.OPENAI_API_KEY:
        raise ProviderError(
            "OpenAI API key not configured. Set OPENAI_API_KEY in your .env file.", 503
        )
    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=_OPENAI_CHAT_MODEL,
            messages=_prepend_system(messages, system_prompt),
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except openai.AuthenticationError:
        raise ProviderError("Invalid OpenAI API key.", 401)
    except openai.RateLimitError:
        raise ProviderError("OpenAI rate limit exceeded. Try again in a moment.", 429)
    except openai.OpenAIError as exc:
        raise ProviderError(f"OpenAI error: {exc}", 500)


def _grade_openai(task, user_answer, max_pts, subject):
    import openai

    if not config.OPENAI_API_KEY:
        raise ProviderError("OpenAI API key not configured.", 503)
    prompt = _grading_prompt(task, user_answer, max_pts, subject)
    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=_OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.3,
        )
        return _parse_grade(response.choices[0].message.content, task, max_pts)
    except openai.AuthenticationError:
        raise ProviderError("Invalid OpenAI API key.", 401)
    except openai.RateLimitError:
        raise ProviderError("OpenAI rate limit exceeded.", 429)
    except openai.OpenAIError as exc:
        raise ProviderError(f"OpenAI grading error: {exc}", 500)


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------

_GEMINI_MODEL = "gemini-2.0-flash"


def _ask_gemini(message, system_prompt):
    import google.generativeai as genai

    if not config.GEMINI_API_KEY:
        raise ProviderError(
            "Gemini API key not configured. Set GEMINI_API_KEY in your .env file.", 503
        )
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=_GEMINI_MODEL,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            message,
            generation_config=genai.GenerationConfig(
                max_output_tokens=1024,
                temperature=0.7,
            ),
        )
        return response.text
    except Exception as exc:
        _raise_gemini_error(exc)


def _ask_gemini_with_history(messages, system_prompt):
    import google.generativeai as genai

    if not config.GEMINI_API_KEY:
        raise ProviderError(
            "Gemini API key not configured. Set GEMINI_API_KEY in your .env file.", 503
        )
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=_GEMINI_MODEL,
            system_instruction=system_prompt,
        )
        # Convert prior messages to Gemini's history format (all but last)
        history = []
        for msg in messages[:-1]:
            role = "model" if msg["role"] == "assistant" else "user"
            history.append({"role": role, "parts": [msg["content"]]})
        last_message = messages[-1]["content"]
        chat = model.start_chat(history=history)
        response = chat.send_message(
            last_message,
            generation_config=genai.GenerationConfig(
                max_output_tokens=1024,
                temperature=0.7,
            ),
        )
        return response.text
    except Exception as exc:
        _raise_gemini_error(exc)


def _grade_gemini(task, user_answer, max_pts, subject):
    import google.generativeai as genai

    if not config.GEMINI_API_KEY:
        raise ProviderError("Gemini API key not configured.", 503)
    prompt = _grading_prompt(task, user_answer, max_pts, subject)
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(_GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                max_output_tokens=512,
                temperature=0.3,
            ),
        )
        return _parse_grade(response.text, task, max_pts)
    except Exception as exc:
        _raise_gemini_error(exc)


def _raise_gemini_error(exc):
    msg = str(exc).lower()
    if any(k in msg for k in ("api_key", "invalid", "403", "permission")):
        raise ProviderError("Invalid Gemini API key.", 401)
    if any(k in msg for k in ("quota", "429", "resource_exhausted")):
        raise ProviderError("Gemini quota exceeded. Try again in a moment.", 429)
    raise ProviderError(f"Gemini error: {exc}", 500)


# ---------------------------------------------------------------------------
# Perplexity  (OpenAI-compatible REST API)
# ---------------------------------------------------------------------------

_PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
_PERPLEXITY_CHAT_MODEL = "sonar"


def _ask_perplexity(message, system_prompt):
    import openai

    if not config.PERPLEXITY_API_KEY:
        raise ProviderError(
            "Perplexity API key not configured. Set PERPLEXITY_API_KEY in your .env file.", 503
        )
    try:
        client = openai.OpenAI(
            api_key=config.PERPLEXITY_API_KEY,
            base_url=_PERPLEXITY_BASE_URL,
        )
        response = client.chat.completions.create(
            model=_PERPLEXITY_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except openai.AuthenticationError:
        raise ProviderError("Invalid Perplexity API key.", 401)
    except openai.RateLimitError:
        raise ProviderError("Perplexity rate limit exceeded. Try again in a moment.", 429)
    except openai.OpenAIError as exc:
        raise ProviderError(f"Perplexity error: {exc}", 500)


def _ask_perplexity_with_history(messages, system_prompt):
    import openai

    if not config.PERPLEXITY_API_KEY:
        raise ProviderError(
            "Perplexity API key not configured. Set PERPLEXITY_API_KEY in your .env file.", 503
        )
    try:
        client = openai.OpenAI(
            api_key=config.PERPLEXITY_API_KEY,
            base_url=_PERPLEXITY_BASE_URL,
        )
        response = client.chat.completions.create(
            model=_PERPLEXITY_CHAT_MODEL,
            messages=_prepend_system(messages, system_prompt),
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except openai.AuthenticationError:
        raise ProviderError("Invalid Perplexity API key.", 401)
    except openai.RateLimitError:
        raise ProviderError("Perplexity rate limit exceeded. Try again in a moment.", 429)
    except openai.OpenAIError as exc:
        raise ProviderError(f"Perplexity error: {exc}", 500)


def _grade_perplexity(task, user_answer, max_pts, subject):
    """Perplexity does not support JSON response mode; we parse JSON from the reply."""
    import openai

    if not config.PERPLEXITY_API_KEY:
        raise ProviderError("Perplexity API key not configured.", 503)
    prompt = (
        _grading_prompt(task, user_answer, max_pts, subject)
        + "\n\nIMPORTANT: Respond with only a valid JSON object. No markdown fences, no extra text."
    )
    try:
        client = openai.OpenAI(
            api_key=config.PERPLEXITY_API_KEY,
            base_url=_PERPLEXITY_BASE_URL,
        )
        response = client.chat.completions.create(
            model=_PERPLEXITY_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.3,
        )
        return _parse_grade(response.choices[0].message.content, task, max_pts)
    except openai.AuthenticationError:
        raise ProviderError("Invalid Perplexity API key.", 401)
    except openai.RateLimitError:
        raise ProviderError("Perplexity rate limit exceeded.", 429)
    except openai.OpenAIError as exc:
        raise ProviderError(f"Perplexity grading error: {exc}", 500)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _prepend_system(messages, system_prompt):
    """Return a new messages list with the system prompt prepended."""
    return [{"role": "system", "content": system_prompt}] + messages


def _grading_prompt(task, user_answer, max_pts, subject):
    question = task.get("question", "")
    rubric = task.get("rubric", "")
    threshold = round(max_pts * 0.7)
    return (
        f"You are grading a student assignment on {subject}.\n\n"
        f"Question ({max_pts} points):\n{question}\n\n"
        f"Grading rubric:\n{rubric}\n\n"
        f"Student's answer:\n{user_answer}\n\n"
        f"Evaluate the answer strictly according to the rubric. "
        f"Respond with a JSON object using exactly these keys:\n"
        f'{{"score": <integer 0 to {max_pts}>, '
        f'"correct": <true if score >= {threshold}, false otherwise>, '
        f'"feedback": "<specific, constructive feedback on what was right and what was missing>", '
        f'"ideal_answer": "<a concise model answer>"}}'
    )


def _parse_grade(raw, task, max_pts):
    """Parse a JSON grading response into a result dict."""
    sample_answer = task.get("sample_answer", "See rubric.")

    # Strip markdown code fences some models add even when told not to
    text = raw.strip()
    if text.startswith("```"):
        # remove opening fence line
        text = text.split("\n", 1)[-1]
        # remove closing fence
        if "```" in text:
            text = text.rsplit("```", 1)[0]
        text = text.strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        data = {}

    score = max(0, min(max_pts, int(data.get("score", 0))))
    threshold = round(max_pts * 0.7)
    return {
        "id": task["id"],
        "type": task.get("type"),
        "score": score,
        "max_score": max_pts,
        "correct": bool(data.get("correct", score >= threshold)),
        "feedback": data.get("feedback", "No feedback available."),
        "ideal_answer": data.get("ideal_answer", sample_answer),
    }
