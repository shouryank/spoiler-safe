from __future__ import annotations

from typing import Iterable, Tuple


MAX_TRANSCRIPT_CHARS = 12000


def format_seconds(seconds: int) -> str:
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60

    if hrs > 0:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def build_context(
    transcript: Iterable[object],
    max_chars: int = MAX_TRANSCRIPT_CHARS,
) -> Tuple[str, int, int]:
    """
    Builds a transcript context window capped by max_chars.
    Keeps the most recent usable lines, which usually helps answer
    scene-specific questions better.
    """
    lines: list[str] = []

    for item in transcript:
        text = normalize_text(getattr(item, "text", ""))
        if not text:
            continue

        start = int(getattr(item, "start", 0))
        timestamp = format_seconds(start)
        lines.append(f"[{timestamp}] {text}")

    selected: list[str] = []
    total_chars = 0

    for line in reversed(lines):
        line_len = len(line) + 1
        if total_chars + line_len > max_chars:
            break
        selected.append(line)
        total_chars += line_len

    selected.reverse()
    context = "\n".join(selected)

    return context, len(selected), total_chars


def build_prompt(
    title: str,
    current_time_human: str,
    question: str,
    context: str,
) -> str:
    return f"""
You are Spoiler Safe, an assistant that answers questions about a video without revealing future events.

Rules:
- Answer ONLY using the transcript context provided below.
- The user has watched only up to timestamp: {current_time_human}.
- NEVER mention anything that could happen after that point.
- If the answer is not clearly supported by the watched transcript, say that the watched portion does not provide enough information yet.
- Do not speculate.
- Be concise, clear, and helpful.
- Prefer phrasing like "Based on what you've watched so far..." when useful.
- If a character, event, or motive is not yet explained in the watched portion, say so plainly.

Video title: {title}
Current watched time: {current_time_human}
User question: {question}

Transcript context up to watched time:
{context}

Now answer the user's question safely.
""".strip()