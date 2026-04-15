"""AI planner service: prompt building, LLM calling, response parsing."""

import json
from typing import Any

import httpx

from app.models import Video


# --- Custom exceptions ---


class AIServiceError(Exception):
    """Base exception for AI service errors."""

    pass


class AIClientError(AIServiceError):
    """Client/timeout errors when calling the LLM."""

    pass


class AIAuthError(AIServiceError):
    """Authentication error (401) from the LLM API."""

    pass


class AIServerError(AIServiceError):
    """Server error (5xx) from the LLM API."""

    pass


class ParseError(AIServiceError):
    """Error parsing the LLM response."""

    pass


# --- Prompt builder ---


def build_prompt(
    videos: list[Video],
    params: dict[str, Any],
) -> list[dict[str, str]]:
    """Build the chat messages for the LLM.

    Args:
        videos: List of Video objects from the library.
        params: Plan parameters (plan_type, focus_areas, days_per_week, etc.).

    Returns:
        List of message dicts with role and content.
    """
    # System message
    system_msg = (
        "You are a professional workout plan generator. "
        "Given a video library and user preferences, you create structured workout plans. "
        "Each plan references videos from the library by their video_id. "
        "You MUST respond with valid JSON only, no extra text."
    )

    # Build library listing
    library_lines = []
    for v in videos:
        library_lines.append(
            f"- video_id={v.id}, title=\"{v.title}\", "
            f"category_id={v.category_id}, "
            f"difficulty={v.difficulty or 'unknown'}, "
            f"duration={v.duration or 'unknown'}s, "
            f"muscle_groups={v.muscle_groups or 'unknown'}"
        )
    library_text = "\n".join(library_lines) if library_lines else "No videos in library."

    # Build parameters text
    params_lines = [f"Plan type: {params.get('plan_type', 'single_session')}"]
    if "focus_areas" in params:
        params_lines.append(f"Focus areas: {', '.join(params['focus_areas'])}")
    if "days_per_week" in params:
        params_lines.append(f"Days per week: {params['days_per_week']}")
    if "duration_weeks" in params:
        params_lines.append(f"Duration in weeks: {params['duration_weeks']}")
    params_text = "\n".join(params_lines)

    # Output format specification
    output_format = """Respond with a JSON object with this exact structure:
{
  "title": "string - name of the plan",
  "plan_type": "single_session|weekly|multi_week",
  "items": [
    {
      "video_id": <integer - must be a valid video_id from the library>,
      "day_position": <integer - which day/session (1-based)>,
      "order_position": <integer - order within the day (1-based)>
    }
  ]
}"""

    user_msg = (
        f"Here is my video library:\n\n{library_text}\n\n"
        f"My preferences:\n{params_text}\n\n"
        f"Generate a workout plan using videos from my library.\n"
        f"Only use video_id values that exist in the library above.\n\n"
        f"{output_format}"
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


# --- LLM caller ---


def call_llm(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    timeout: float = 60.0,
) -> str:
    """Call the OpenAI-compatible LLM API.

    Args:
        base_url: API base URL (e.g. https://api.openai.com/v1).
        api_key: API key for authentication.
        model: Model name (e.g. gpt-4).
        messages: Chat messages to send.
        temperature: Sampling temperature.
        timeout: Request timeout in seconds.

    Returns:
        The content string from the LLM response.

    Raises:
        AIClientError: On timeout or connection error.
        AIAuthError: On 401 response.
        AIServerError: On 5xx response.
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    try:
        response = httpx.post(
            url,
            headers=headers,
            json=body,
            timeout=timeout,
        )
    except httpx.TimeoutException as e:
        raise AIClientError(f"LLM request timeout: {e}") from e
    except httpx.RequestError as e:
        raise AIClientError(f"LLM request error: {e}") from e

    if response.status_code == 401:
        raise AIAuthError(f"LLM API authentication failed (401): {response.text}")

    if response.status_code >= 500:
        raise AIServerError(
            f"LLM API server error ({response.status_code}): {response.text}"
        )

    if response.status_code != 200:
        raise AIClientError(
            f"LLM API error ({response.status_code}): {response.text}"
        )

    data = response.json()
    return data["choices"][0]["message"]["content"]


# --- Response parser ---


def parse_response(
    response_text: str,
    valid_video_ids: set[int],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse the LLM response into plan data and items.

    Args:
        response_text: Raw text from the LLM.
        valid_video_ids: Set of valid video IDs to validate against.

    Returns:
        Tuple of (plan_data dict, items list).

    Raises:
        ParseError: If the response is malformed or contains invalid references.
    """
    # Try to extract JSON from markdown code blocks
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end])

    # Parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ParseError(f"Failed to parse LLM response as JSON: {e}") from e

    # Validate required fields
    if "title" not in data:
        raise ParseError("LLM response missing 'title' field")
    if "plan_type" not in data:
        raise ParseError("LLM response missing 'plan_type' field")
    if "items" not in data or not isinstance(data["items"], list):
        raise ParseError("LLM response missing 'items' array")

    # Validate video IDs in items
    invalid_ids = []
    for item in data["items"]:
        vid = item.get("video_id")
        if vid is not None and vid not in valid_video_ids:
            invalid_ids.append(vid)

    if invalid_ids:
        raise ParseError(
            f"Plan references non-existent video IDs: {invalid_ids}"
        )

    plan_data = {
        "title": data["title"],
        "plan_type": data["plan_type"],
    }

    items = [
        {
            "video_id": item["video_id"],
            "day_position": item["day_position"],
            "order_position": item["order_position"],
        }
        for item in data["items"]
    ]

    return plan_data, items
