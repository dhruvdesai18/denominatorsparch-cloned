"""
Shared OpenAI client for the 3 planned LLM calls in the pipeline
(Agents #1, #2, #5). All LLM calls in this project go through here so the
model choice and API key handling stay in one place.

Provider: OpenAI (gpt-4o-mini by default). The original 14-day plan assumed
Anthropic/Claude for these calls -- switched to OpenAI because that's the
API key the team has. See config/token_counter.py for the resulting budget
note.
"""

import os

from openai import OpenAI

DEFAULT_MODEL = "gpt-4o-mini"

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it in your shell before "
                "running any agent that makes an LLM call."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def chat_json(prompt: str, model: str = DEFAULT_MODEL) -> tuple[str, int, int]:
    """Send one prompt, force a JSON object response. Returns
    (raw_json_text, prompt_tokens, completion_tokens)."""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    return content, prompt_tokens, completion_tokens
