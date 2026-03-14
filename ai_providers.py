"""
AI provider abstraction layer for LinuxNLearn.

Supported providers
-------------------
  openai      – OpenAI GPT-4o-mini (chat.completions)
  gemini      – Google Gemini 2.0 Flash (google-generativeai)
    perplexity  – Perplexity Sonar (official perplexityai SDK)

The active provider is chosen by:
  1. The ``provider`` argument passed to ask() / grade_open_ended()
  2. config.AI_PROVIDER  (set AI_PROVIDER= in .env)
  3. First provider whose API key is configured
"""

import json
from typing import Generator

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


def _is_configured_key(value):
    """Return True only for likely real API keys, not example placeholders."""
    if not value:
        return False
    cleaned = str(value).strip()
    if not cleaned:
        return False
    lower = cleaned.lower()
    placeholder_markers = (
        "your_",
        "replace_me",
        "changeme",
        "example",
        "placeholder",
    )
    return not any(marker in lower for marker in placeholder_markers)


def get_available_providers():
    """Return a list of provider names whose API keys are configured."""
    available = []
    if _is_configured_key(config.OPENAI_API_KEY):
        available.append("openai")
    if _is_configured_key(config.GEMINI_API_KEY):
        available.append("gemini")
    if _is_configured_key(config.PERPLEXITY_API_KEY):
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


def ask_chat(message, system_prompt=None, provider=None, chat_options=None):
    """
    Send a chat message and return enriched response data for UI rendering.

    Returns a dict with at least:
      reply: str
      provider: str
    Optionally for Perplexity:
      citations: list[str]
      search_results: list[dict]
      usage: dict
      model: str
    """
    if system_prompt is None:
        system_prompt = EDUCATION_SYSTEM_PROMPT

    resolved_provider = resolve_provider(provider)
    if resolved_provider == "perplexity":
        return _ask_perplexity_chat(message, system_prompt, chat_options=chat_options)

    return {
        "reply": ask(message, system_prompt=system_prompt, provider=resolved_provider),
        "provider": resolved_provider,
    }


def stream_chat(message, system_prompt=None, provider=None, chat_options=None) -> Generator[dict, None, None]:
    """
    Stream chat events for UI.

    Yields event dicts with keys:
      event: "delta" | "done"
      data: event payload dict
    """
    if system_prompt is None:
        system_prompt = EDUCATION_SYSTEM_PROMPT

    resolved_provider = resolve_provider(provider)
    if resolved_provider == "perplexity":
        yield from _stream_perplexity_chat(message, system_prompt, chat_options=chat_options)
        return

    payload = {
        "reply": ask(message, system_prompt=system_prompt, provider=resolved_provider),
        "provider": resolved_provider,
    }
    if payload["reply"]:
        yield {"event": "delta", "data": {"text": payload["reply"]}}
    yield {"event": "done", "data": payload}


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

    if not _is_configured_key(config.OPENAI_API_KEY):
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
    except TypeError as exc:
        raise ProviderError(
            f"OpenAI client compatibility error: {exc}. Try updating dependencies.",
            500,
        )
    except openai.OpenAIError as exc:
        raise ProviderError(f"OpenAI error: {exc}", 500)


def _ask_openai_with_history(messages, system_prompt):
    import openai

    if not _is_configured_key(config.OPENAI_API_KEY):
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
    except TypeError as exc:
        raise ProviderError(
            f"OpenAI client compatibility error: {exc}. Try updating dependencies.",
            500,
        )
    except openai.OpenAIError as exc:
        raise ProviderError(f"OpenAI error: {exc}", 500)


def _grade_openai(task, user_answer, max_pts, subject):
    import openai

    if not _is_configured_key(config.OPENAI_API_KEY):
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
    except TypeError as exc:
        raise ProviderError(
            f"OpenAI client compatibility error: {exc}. Try updating dependencies.",
            500,
        )
    except openai.OpenAIError as exc:
        raise ProviderError(f"OpenAI grading error: {exc}", 500)


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------

_GEMINI_MODEL = "gemini-2.5-flash"


def _ask_gemini(message, system_prompt):
    import google.generativeai as genai

    if not _is_configured_key(config.GEMINI_API_KEY):
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

    if not _is_configured_key(config.GEMINI_API_KEY):
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

    if not _is_configured_key(config.GEMINI_API_KEY):
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
# Perplexity (official SDK)
# ---------------------------------------------------------------------------

_PERPLEXITY_CHAT_MODEL = "sonar"


def _new_perplexity_client():
    from perplexity import Perplexity

    return Perplexity(api_key=config.PERPLEXITY_API_KEY)


def _ask_perplexity(message, system_prompt):
    if not _is_configured_key(config.PERPLEXITY_API_KEY):
        raise ProviderError(
            "Perplexity API key not configured. Set PERPLEXITY_API_KEY in your .env file.", 503
        )
    try:
        client = _new_perplexity_client()
        response = client.chat.completions.create(
            model=_PERPLEXITY_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return _extract_choice_content(response)
    except Exception as exc:
        _raise_perplexity_error(exc)


def _ask_perplexity_chat(message, system_prompt, chat_options=None):
    """Return Perplexity response enriched with metadata useful for the chat UI."""
    if not _is_configured_key(config.PERPLEXITY_API_KEY):
        raise ProviderError(
            "Perplexity API key not configured. Set PERPLEXITY_API_KEY in your .env file.", 503
        )
    try:
        client = _new_perplexity_client()
        request_payload = {
            "model": _PERPLEXITY_CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
        }
        request_payload.update(_build_perplexity_chat_options(chat_options))
        response = client.chat.completions.create(**request_payload)

        payload = {
            "reply": _extract_choice_content(response),
            "provider": "perplexity",
            "model": getattr(response, "model", _PERPLEXITY_CHAT_MODEL),
        }

        citations = getattr(response, "citations", None)
        if citations:
            payload["citations"] = list(citations)

        search_results = getattr(response, "search_results", None)
        if search_results:
            payload["search_results"] = [_to_plain(item) for item in search_results]

        usage = getattr(response, "usage", None)
        if usage:
            payload["usage"] = _to_plain(usage)

        return payload
    except Exception as exc:
        _raise_perplexity_error(exc)


def _stream_perplexity_chat(message, system_prompt, chat_options=None):
    """Yield streamed Perplexity deltas and a final done payload."""
    if not _is_configured_key(config.PERPLEXITY_API_KEY):
        raise ProviderError(
            "Perplexity API key not configured. Set PERPLEXITY_API_KEY in your .env file.", 503
        )

    try:
        client = _new_perplexity_client()
        request_payload = {
            "model": _PERPLEXITY_CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
            "stream": True,
        }
        request_payload.update(_build_perplexity_chat_options(chat_options))
        stream = client.chat.completions.create(**request_payload)

        text_parts = []
        final_payload = {
            "provider": "perplexity",
            "model": _PERPLEXITY_CHAT_MODEL,
        }

        for chunk in stream:
            # Track metadata if present on stream chunks.
            if getattr(chunk, "model", None):
                final_payload["model"] = chunk.model
            if getattr(chunk, "citations", None):
                final_payload["citations"] = list(chunk.citations)
            if getattr(chunk, "search_results", None):
                final_payload["search_results"] = [_to_plain(x) for x in chunk.search_results]
            if getattr(chunk, "usage", None):
                final_payload["usage"] = _to_plain(chunk.usage)

            choices = getattr(chunk, "choices", []) or []
            if not choices:
                continue

            content = _extract_choice_content(chunk)
            if content:
                text_parts.append(content)
                yield {"event": "delta", "data": {"text": content}}

        final_payload["reply"] = "".join(text_parts)
        yield {"event": "done", "data": final_payload}
    except Exception as exc:
        _raise_perplexity_error(exc)


def _ask_perplexity_with_history(messages, system_prompt):
    if not _is_configured_key(config.PERPLEXITY_API_KEY):
        raise ProviderError(
            "Perplexity API key not configured. Set PERPLEXITY_API_KEY in your .env file.", 503
        )
    try:
        client = _new_perplexity_client()
        response = client.chat.completions.create(
            model=_PERPLEXITY_CHAT_MODEL,
            messages=_prepend_system(messages, system_prompt),
            max_tokens=1024,
            temperature=0.7,
        )
        return _extract_choice_content(response)
    except Exception as exc:
        _raise_perplexity_error(exc)


def _grade_perplexity(task, user_answer, max_pts, subject):
    """Perplexity does not support JSON response mode; we parse JSON from the reply."""
    if not _is_configured_key(config.PERPLEXITY_API_KEY):
        raise ProviderError("Perplexity API key not configured.", 503)
    prompt = (
        _grading_prompt(task, user_answer, max_pts, subject)
        + "\n\nIMPORTANT: Respond with only a valid JSON object. No markdown fences, no extra text."
    )
    try:
        client = _new_perplexity_client()
        response = client.chat.completions.create(
            model=_PERPLEXITY_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.3,
        )
        return _parse_grade(_extract_choice_content(response), task, max_pts)
    except Exception as exc:
        _raise_perplexity_error(exc)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _prepend_system(messages, system_prompt):
    """Return a new messages list with the system prompt prepended."""
    return [{"role": "system", "content": system_prompt}] + messages


def _extract_choice_content(response_obj):
    """Extract text content from OpenAI-style choice message/delta structures."""
    choices = getattr(response_obj, "choices", []) or []
    if not choices:
        return ""

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)
    if message:
        content = getattr(message, "content", None)
        if content:
            return content

    delta = getattr(first_choice, "delta", None)
    if delta:
        content = getattr(delta, "content", None)
        if content:
            return content

    return ""


def _raise_perplexity_error(exc):
    """Normalize perplexity SDK exceptions to ProviderError for API responses."""
    if isinstance(exc, ModuleNotFoundError) and getattr(exc, "name", "") == "perplexity":
        raise ProviderError("Perplexity SDK not installed. Install dependencies from requirements.txt.", 500)

    import perplexity

    if isinstance(exc, perplexity.AuthenticationError):
        raise ProviderError("Invalid Perplexity API key.", 401)
    if isinstance(exc, perplexity.RateLimitError):
        raise ProviderError("Perplexity rate limit exceeded. Try again in a moment.", 429)
    if isinstance(exc, perplexity.APIStatusError):
        status_code = getattr(exc, "status_code", 500) or 500
        if status_code == 401:
            raise ProviderError("Invalid Perplexity API key.", 401)
        if status_code == 429:
            raise ProviderError("Perplexity rate limit exceeded. Try again in a moment.", 429)
        raise ProviderError(f"Perplexity API error: {exc}", int(status_code))
    if isinstance(exc, perplexity.APIConnectionError):
        raise ProviderError("Perplexity connection error. Please try again.", 502)
    if isinstance(exc, TypeError):
        raise ProviderError(
            f"Perplexity client compatibility error: {exc}. Try updating dependencies.",
            500,
        )
    raise ProviderError(f"Perplexity error: {exc}", 500)


def _to_plain(value):
    """Convert SDK model objects to plain Python dict/list types for JSON responses."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if hasattr(value, "__dict__"):
        return _to_plain(vars(value))
    return str(value)


def _build_perplexity_chat_options(chat_options):
    """Whitelist and normalize optional Perplexity chat/search settings from UI."""
    if not isinstance(chat_options, dict):
        return {}

    options = {}

    search_mode = chat_options.get("search_mode")
    if search_mode in {"web", "academic", "sec"}:
        options["search_mode"] = search_mode

    recency = chat_options.get("search_recency_filter")
    if recency in {"hour", "day", "week", "month", "year"}:
        options["search_recency_filter"] = recency

    domain_filter = chat_options.get("search_domain_filter")
    if isinstance(domain_filter, list):
        clean_domains = [str(d).strip() for d in domain_filter if str(d).strip()]
        if clean_domains:
            options["search_domain_filter"] = clean_domains

    safe_search = chat_options.get("safe_search")
    if isinstance(safe_search, bool):
        options["safe_search"] = safe_search

    return_related = chat_options.get("return_related_questions")
    if isinstance(return_related, bool):
        options["return_related_questions"] = return_related

    return options


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
