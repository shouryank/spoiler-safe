from __future__ import annotations

from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.llm import generate_spoiler_safe_answer
from backend.rag import build_prompt, retrieve_context


app = FastAPI(title="Spoiler Safe Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptItem(BaseModel):
    start: float
    dur: Optional[float] = 0
    text: str


class AskRequest(BaseModel):
    title: str
    video_id: Optional[str] = None
    current_time: int
    current_time_human: str
    question: str
    transcript: List[TranscriptItem] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: str
    context_lines_used: int
    context_chars_used: int


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest) -> AskResponse:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not req.transcript:
        raise HTTPException(status_code=400, detail="Transcript is empty.")

    try:
        context, context_lines_used, context_chars_used = retrieve_context(
            transcript=req.transcript,
            video_id=req.video_id or f"untitled:{req.title}",
            current_time=req.current_time,
            question=req.question,
        )
    except (requests.RequestException, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"Embedding retrieval failed: {exc}") from exc
    if not context.strip():
        raise HTTPException(status_code=400, detail="No usable transcript context found.")

    prompt = build_prompt(
        title=req.title,
        current_time_human=req.current_time_human,
        question=req.question,
        context=context,
    )

    answer = generate_spoiler_safe_answer(prompt)
    if not answer:
        answer = "I couldn't generate a spoiler-safe answer from the watched portion."

    return AskResponse(
        answer=answer,
        context_lines_used=context_lines_used,
        context_chars_used=context_chars_used,
    )
