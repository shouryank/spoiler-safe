from __future__ import annotations
from typing import Optional
import os
import requests


def _ollama_generate(prompt: str, model: str = "llama3.1:8b") -> str:
    """
    Uses local Ollama server at http://localhost:11434.
    Install: https://ollama.com/
    Run: ollama serve
    Pull model: ollama pull llama3.1:8b
    """
    url = "http://localhost:11434/api/generate"
    resp = requests.post(url, json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3}
    }, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def _openai_compatible_generate(prompt: str) -> str:
    """
    Optional: If you have an OpenAI-compatible endpoint.
    Set:
      LLM_BASE_URL (e.g., https://api.openai.com/v1)
      LLM_API_KEY
      LLM_MODEL (e.g., gpt-4o-mini)
    This uses the Chat Completions API shape.
    """
    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if not base_url or not api_key:
        raise RuntimeError("LLM_BASE_URL and LLM_API_KEY must be set for OpenAI-compatible mode.")

    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


def generate(prompt: str) -> str:
    """
    Default to Ollama.
    If USE_OPENAI_COMPAT=1, use OpenAI-compatible endpoint.
    """
    use_openai = os.environ.get("USE_OPENAI_COMPAT", "0") == "1"
    if use_openai:
        return _openai_compatible_generate(prompt)

    model = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
    return _ollama_generate(prompt, model=model)