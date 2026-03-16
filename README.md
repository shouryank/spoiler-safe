# Spoiler-Safe Movie Q&A

A browser extension that lets you ask questions about a movie or video **without getting spoiled about future scenes**.

The extension only uses the **context from the video up to the current timestamp**, allowing viewers to clarify plot points, characters, or dialogue safely while watching.

---

## Why I Built This

I often watch movies and long videos in multiple sittings.  
Sometimes I forget a character, a plot detail, or the context of a scene.

Looking it up online almost always leads to **spoilers for future parts of the movie**.

This project explores a simple idea:

> What if you could ask questions about the movie and only get answers from what you've already watched?

---

## How It Works (Concept)

1. The extension tracks the **current timestamp of the video**
2. It extracts the **subtitle/transcript context up to that timestamp**
3. That partial transcript is used as context for an **AI Q&A system**
4. The AI answers questions **only from the watched portion**

This allows users to ask things like:

- "Who is this character again?"
- "Why are they going to this location?"
- "What happened in the last scene?"

Without revealing future plot details.

---

## Current Challenge

The biggest technical challenge right now is **reliably extracting the context of the movie in real time**.

The initial prototype attempted to **read subtitles directly from the screen / DOM**, which is fragile and inconsistent across players.

I am currently exploring a better approach:

- Using **backend transcript endpoints (e.g., YouTube's transcript API)**  
- Fetching subtitles programmatically
- Limiting the transcript **only up to the current timestamp**

This would allow the extension to build **clean contextual windows** for the AI without relying on screen scraping.

---

## Planned Improvements

- Reliable subtitle extraction via transcript APIs
- Timestamp-aware context chunking
- Spoiler-safe prompt engineering
- Support for multiple platforms (YouTube first, then Netflix if possible)
- Better UI for asking questions during playback

---

## Tech Stack (Planned / Experimental)

- Browser Extension (Chrome)
- JavaScript / TypeScript
- AI / LLM integration
- Transcript APIs
- Context window filtering by timestamp

---

## Collaboration

This is an **experimental project**, and I'm actively exploring better ways to implement the context extraction and spoiler-safe logic.

If you have ideas related to:

- subtitle extraction
- timestamp-aware RAG
- browser extensions
- movie context retrieval
- AI-assisted video tools

I'd love to collaborate or hear your suggestions.

Feel free to open an issue or reach out.

---

## Author

**Shourya N Kumar**  
MCS @ NC State University  

Portfolio:  
https://shouryank01.framer.ai
