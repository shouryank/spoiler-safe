from __future__ import annotations
from typing import List, Literal, Optional, Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel, Field
from rag import TfidfRAG, Chunk
from llm import generate


Mode = Literal["strict", "hint", "full"]


class SubtitleCue(BaseModel):
    start: float
    end: float
    text: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    platform: Literal["youtube", "netflix"]
    title: str
    current_time: float = Field(ge=0)
    duration: Optional[float] = Field(default=None, ge=0)
    mode: Mode
    question: str
    # "seen" subtitle cues only (the extension will already clip for strict/hint),
    # but backend also re-filters for safety.
    subtitle_cues: List[SubtitleCue] = Field(default_factory=list)
    history: List[ChatMessage] = Field(default_factory=list)


class Citation(BaseModel):
    start: float
    end: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    used_mode: Mode
    safe_cutoff_time: float


app = FastAPI(title="Spoiler-Safe Movie Q&A (MVP)")
rag = TfidfRAG()


def build_prompt(req: ChatRequest, retrieved: List[Chunk]) -> str:
    # Keep prompt compact; grounded in retrieved chunks only.
    context_lines = []
    for c in retrieved:
        context_lines.append(f"[{fmt_time(c.start)}–{fmt_time(c.end)}] {c.text}")

    context = "\n".join(context_lines).strip()

    # History: last few turns only
    history = req.history[-6:]
    history_text = "\n".join([f"{m.role.upper()}: {m.content}" for m in history])

    mode_rules = {
        "strict": (
            "You MUST answer using ONLY the provided context (subtitles up to the cutoff time). "
            "If the question requires future events not in context, say you can't answer yet without spoilers. "
            "Do NOT guess."
        ),
        "hint": (
            "You MUST answer using ONLY the provided context. "
            "Give gentle hints and clarifications without revealing or concluding anything that depends on future scenes. "
            "Prefer questions back to the user, or point to what was said/shown so far."
        ),
        "full": (
            "You may answer freely using the provided context. "
            "If context is insufficient, you can still infer, but clearly label it as inference."
        ),
    }[req.mode]

    prompt = f"""
You are a spoiler-safe movie assistant.
Platform: {req.platform}
Title: {req.title}
Cutoff time: {fmt_time(req.current_time)}
Mode: {req.mode}

RULES:
- {mode_rules}
- Cite supporting context with timestamps when possible.
- Keep the answer concise, helpful, and conversational.

CONVERSATION (recent):
{history_text}

CONTEXT (subtitles / seen so far):
{context}

USER QUESTION:
{req.question}

ASSISTANT:
""".strip()

    return prompt


def fmt_time(seconds: float) -> str:
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    # Safety re-filter: only allow cues <= cutoff for strict/hint
    safe_cutoff = req.current_time if req.mode in ("strict", "hint") else float("inf")

    safe_cues = []
    for c in req.subtitle_cues:
        if c.end <= safe_cutoff:
            safe_cues.append(c)

    chunks = [Chunk(start=c.start, end=c.end, text=c.text) for c in safe_cues if c.text.strip()]
    retrieved_pairs = rag.retrieve(req.question, chunks, k=7)
    retrieved = [cp[0] for cp in retrieved_pairs]

    # If strict/hint and we have no context, refuse safely
    if req.mode in ("strict", "hint") and len(retrieved) == 0:
        return ChatResponse(
            answer=(
                "I don’t have enough *seen-so-far* context to answer that without risking spoilers. "
                "Try enabling captions (YouTube) or uploading subtitles (SRT/VTT), then ask again."
            ),
            citations=[],
            used_mode=req.mode,
            safe_cutoff_time=req.current_time
        )

    prompt = build_prompt(req, retrieved)
    answer = generate(prompt)

    # Provide citations as the retrieved chunks (trim to top 4)
    citations = []
    for c in retrieved[:4]:
        citations.append(Citation(start=c.start, end=c.end, text=c.text[:180]))

    # Extra hard safety: if strict/hint, never cite beyond cutoff (already filtered)
    return ChatResponse(
        answer=answer,
        citations=citations,
        used_mode=req.mode,
        safe_cutoff_time=req.current_time
    )