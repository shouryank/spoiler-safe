const BACKEND_URL = "http://127.0.0.1:8000";

let panelMounted = false;
let panelVisible = false;
let transcriptCache = null;
let transcriptCacheVideoId = null;
let lastDomSubtitleBuffer = [];

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "TOGGLE_SPOILER_SAFE_PANEL") {
    togglePanel();
  }
});

function togglePanel() {
  if (!panelMounted) {
    mountPanel();
    panelMounted = true;
  }

  const root = document.getElementById("spoiler-safe-root");
  if (!root) return;

  panelVisible = !panelVisible;
  root.classList.toggle("spsf-hidden", !panelVisible);
}

function mountPanel() {
  if (document.getElementById("spoiler-safe-root")) return;

  const root = document.createElement("div");
  root.id = "spoiler-safe-root";
  root.className = "spsf-hidden";

  root.innerHTML = `
    <div class="spsf-panel">
      <div class="spsf-header">
        <div class="spsf-title">
          <h2>Spoiler Safe</h2>
          <p>Answers only from what you've watched so far</p>
        </div>
        <button class="spsf-close" id="spsf-close-btn">&times;</button>
      </div>

      <div class="spsf-body">
        <div class="spsf-chip-row">
          <button class="spsf-chip">Who is this character again?</button>
          <button class="spsf-chip">What just happened?</button>
          <button class="spsf-chip">Why are they here?</button>
        </div>

        <div class="spsf-status" id="spsf-status">Ready.</div>

        <textarea
          id="spsf-question"
          class="spsf-question"
          placeholder="Ask a spoiler-safe question about the current scene..."
        ></textarea>

        <div class="spsf-actions">
          <button id="spsf-ask-btn" class="spsf-btn spsf-btn-primary">Ask</button>
          <button id="spsf-refresh-btn" class="spsf-btn spsf-btn-secondary">Refresh Context</button>
        </div>

        <div class="spsf-answer" id="spsf-answer">No answer yet.</div>
        <div class="spsf-meta" id="spsf-meta"></div>
      </div>
    </div>
  `;

  document.body.appendChild(root);

  document.getElementById("spsf-close-btn")?.addEventListener("click", () => {
    root.classList.add("spsf-hidden");
    panelVisible = false;
  });

  document.getElementById("spsf-ask-btn")?.addEventListener("click", handleAsk);
  document.getElementById("spsf-refresh-btn")?.addEventListener("click", async () => {
    setStatus("Refreshing transcript context...");
    transcriptCache = null;
    transcriptCacheVideoId = null;
    lastDomSubtitleBuffer = [];
    await getTranscriptContext(true);
    setStatus("Context refreshed.");
  });

  document.querySelectorAll(".spsf-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const textarea = document.getElementById("spsf-question");
      textarea.value = chip.textContent.trim();
    });
  });
}

function getVideoElement() {
  return document.querySelector("video");
}

function getCurrentTimestamp() {
  const video = getVideoElement();
  return video ? Math.floor(video.currentTime || 0) : 0;
}

function getVideoTitle() {
  const title =
    document.querySelector("h1.ytd-watch-metadata yt-formatted-string")?.textContent ||
    document.title ||
    "Unknown Video";
  return title.trim();
}

function getVideoId() {
  const url = new URL(window.location.href);
  return url.searchParams.get("v");
}

function formatTime(seconds) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hrs > 0) {
    return `${hrs}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function setStatus(text, loading = false) {
  const status = document.getElementById("spsf-status");
  if (!status) return;
  status.innerHTML = loading ? `<span class="spsf-loader"></span>${text}` : text;
}

function setAnswer(text) {
  const answer = document.getElementById("spsf-answer");
  if (answer) answer.textContent = text;
}

function setMeta(text) {
  const meta = document.getElementById("spsf-meta");
  if (meta) meta.textContent = text;
}

function parseXmlTranscript(xmlText) {
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlText, "text/xml");
  const textNodes = Array.from(xmlDoc.getElementsByTagName("text"));

  return textNodes.map((node) => {
    const start = parseFloat(node.getAttribute("start") || "0");
    const dur = parseFloat(node.getAttribute("dur") || "0");
    const text = decodeHtml(node.textContent || "").replace(/\s+/g, " ").trim();

    return {
      start,
      dur,
      text
    };
  }).filter((item) => item.text);
}

function decodeHtml(str) {
  const txt = document.createElement("textarea");
  txt.innerHTML = str;
  return txt.value;
}

async function fetchTranscriptFromCaptionTrack() {
  const scripts = Array.from(document.scripts)
    .map((s) => s.textContent || "")
    .filter(Boolean);

  let captionUrl = null;

  for (const content of scripts) {
    if (!content.includes("captionTracks")) continue;

    const match = content.match(/"captionTracks":(\[.*?\])/);
    if (!match) continue;

    try {
      const tracks = JSON.parse(match[1].replace(/\\"/g, '"'));
      if (Array.isArray(tracks) && tracks.length > 0) {
        captionUrl = tracks[0].baseUrl;
        break;
      }
    } catch (error) {
      console.warn("captionTracks parse failed:", error);
    }
  }

  if (!captionUrl && window.ytInitialPlayerResponse?.captions?.playerCaptionsTracklistRenderer?.captionTracks?.length) {
    captionUrl =
      window.ytInitialPlayerResponse.captions.playerCaptionsTracklistRenderer.captionTracks[0].baseUrl;
  }

  if (!captionUrl) {
    throw new Error("No YouTube caption track found.");
  }

  const response = await fetch(captionUrl);
  if (!response.ok) {
    throw new Error(`Caption fetch failed with status ${response.status}`);
  }

  const xmlText = await response.text();
  return parseXmlTranscript(xmlText);
}

function readVisibleDomSubtitles() {
  const selectors = [
    ".ytp-caption-segment",
    ".captions-text .caption-visual-line",
    ".ytp-caption-window-container .ytp-caption-segment"
  ];

  const texts = [];

  for (const selector of selectors) {
    const nodes = document.querySelectorAll(selector);
    nodes.forEach((node) => {
      const text = node.textContent?.trim();
      if (text) texts.push(text);
    });
  }

  const merged = texts.join(" ").replace(/\s+/g, " ").trim();
  if (!merged) return;

  const current = getCurrentTimestamp();
  const last = lastDomSubtitleBuffer[lastDomSubtitleBuffer.length - 1];

  if (!last || last.text !== merged) {
    lastDomSubtitleBuffer.push({
      start: current,
      dur: 2,
      text: merged
    });

    if (lastDomSubtitleBuffer.length > 500) {
      lastDomSubtitleBuffer = lastDomSubtitleBuffer.slice(-500);
    }
  }
}

setInterval(() => {
  if (window.location.hostname.includes("youtube.com")) {
    readVisibleDomSubtitles();
  }
}, 1200);

async function getTranscriptContext(forceRefresh = false) {
  const videoId = getVideoId();
  const currentTime = getCurrentTimestamp();

  if (!videoId) {
    throw new Error("Could not determine YouTube video ID.");
  }

  if (!forceRefresh && transcriptCache && transcriptCacheVideoId === videoId) {
    return filterTranscriptUpToTime(transcriptCache, currentTime);
  }

  try {
    const transcript = await fetchTranscriptFromCaptionTrack();
    transcriptCache = transcript;
    transcriptCacheVideoId = videoId;
    return filterTranscriptUpToTime(transcript, currentTime);
  } catch (error) {
    console.warn("Primary transcript fetch failed, using DOM fallback:", error);

    if (!lastDomSubtitleBuffer.length) {
      throw new Error("Could not retrieve transcript from captions or DOM subtitles.");
    }

    transcriptCache = [...lastDomSubtitleBuffer];
    transcriptCacheVideoId = videoId;
    return filterTranscriptUpToTime(transcriptCache, currentTime);
  }
}

function filterTranscriptUpToTime(transcript, currentTime) {
  return transcript.filter((item) => item.start <= currentTime);
}

async function handleAsk() {
  const question = document.getElementById("spsf-question")?.value?.trim();
  if (!question) {
    setStatus("Please enter a question.");
    return;
  }

  try {
    setStatus("Collecting transcript context...", true);
    setAnswer("Working on your spoiler-safe answer...");
    setMeta("");

    const currentTime = getCurrentTimestamp();
    const title = getVideoTitle();
    const videoId = getVideoId();
    const transcript = await getTranscriptContext(false);

    if (!transcript.length) {
      throw new Error("No transcript context available yet.");
    }

    setStatus("Sending spoiler-safe context to backend...", true);

    const response = await fetch(`${BACKEND_URL}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        title,
        video_id: videoId,
        current_time: currentTime,
        current_time_human: formatTime(currentTime),
        question,
        transcript
      })
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Backend error ${response.status}: ${text}`);
    }

    const data = await response.json();

    setAnswer(data.answer || "No answer returned.");
    setMeta(`Context through ${formatTime(currentTime)} · ${data.context_lines_used} retrieved chunks · ${data.context_chars_used} characters`);
    setStatus("Ready.");
  } catch (error) {
    console.error(error);
    setAnswer(`Error: ${error.message}`);
    setStatus("Something went wrong.");
  }
}
