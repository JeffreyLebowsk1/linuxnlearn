"""
Instructor agent for LinuxNLearn.

Provides a structured, multi-turn AI teaching experience that guides students
through IT topics with context-aware instruction, examples, and comprehension
checks.
"""

import ai_providers

INSTRUCTOR_SYSTEM_PROMPT = (
    "You are an expert IT instructor specializing in networking, Cisco technologies, "
    "Python programming, and Linux administration. Your teaching style is structured, "
    "engaging, and adapted to the student's level.\n\n"
    "As an instructor you:\n"
    "- Start by briefly assessing the student's current knowledge\n"
    "- Break complex topics into clearly ordered, digestible steps\n"
    "- Use real-world analogies and practical examples\n"
    "- Include CLI commands, config snippets, or code the student can run immediately\n"
    "- Periodically check the student's understanding with a short question or exercise\n"
    "- Give specific, constructive feedback on their answers\n"
    "- Suggest logical next steps and related topics to explore\n\n"
    "Format your responses with clear structure: use numbered steps, bullet points, "
    "and fenced code blocks where appropriate. Keep each reply focused — teach one "
    "concept at a time and invite the student to ask follow-up questions."
)


def ask(messages, subject=None, provider=None):
    """
    Send a conversation history to the instructor agent and return its reply.

    Parameters
    ----------
    messages : list[dict]
        Conversation history in the form
        [{"role": "user"|"assistant", "content": "..."}].
        Must contain at least one message.
    subject : str | None
        The current learning subject (e.g. "Linux", "Networking").
        When provided it is appended to the system prompt for added context.
    provider : str | None
        AI provider override; resolved automatically when None.

    Returns
    -------
    str  – the instructor's reply

    Raises
    ------
    ai_providers.ProviderError
    ValueError  – if messages is empty
    """
    if not messages:
        raise ValueError("messages must not be empty")

    system_prompt = INSTRUCTOR_SYSTEM_PROMPT
    if subject:
        system_prompt += f"\n\nThe student is currently studying: {subject}."

    return ai_providers.ask_with_history(
        messages, system_prompt=system_prompt, provider=provider
    )
