const BACKEND_URL = "http://localhost:8000/chat";

let pageState = null;
let subtitleOverride = []; // from uploaded file
let history = [];

function fmtTime(seconds) {
  const s = Math.floor(seconds || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  return `${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
}

function addMsg(role, text, citations=[]) {
  const chat = document.getElementById("chat");
  const div = document.createElement("div");
  div.className = `msg ${role === "user" ? "user" : "bot"}`;
  div.textContent = text;

  if (role === "assistant" && citations && citations.length) {
    const cites = document.createElement("div");
    cites.className = "cites";
    cites.innerHTML = "<b>Sources:</b>";
    citations.forEach(c => {
      const item = document.createElement("div");
      item.className = "citeItem";
      item.textContent = `[${fmtTime(c.start)}–${fmtTime(c.end)}] ${c.text}`;
      cites.appendChild(item);
    });
    div.appendChild(cites);
  }

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function requestPageState() {
  const tab = await getActiveTab();
  if (!tab?.id) return null;

  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tab.id, { type: "GET_STATE" }, (resp) => {
      resolve(resp || null);
    });
  });
}

function updateUIFromState(state) {
  const status = document.getElementById("status");
  const titleEl = document.getElementById("movieTitle");
  const timeNowEl = document.getElementById("timeNow");
  const timeDurEl = document.getElementById("timeDur");
  const platformEl = document.getElementById("platform");

  if (!state) {
    status.textContent = "Open Netflix/YouTube and start playback.";
    return;
  }

  platformEl.textContent = state.platform || "—";
  titleEl.textContent = state.title || "—";
  timeNowEl.textContent = state.currentTime != null ? fmtTime(state.currentTime) : "—";
  timeDurEl.textContent = state.duration ? ` / ${fmtTime(state.duration)}` : "";
  status.textContent = state.ok ? "Ready." : (state.error || "Waiting for player…");
}

function getSeenCues(state, mode) {
  // Prefer captured cues from page when available; fall back to uploaded subtitles
  const currentTime = state?.currentTime ?? 0;

  const cues = (state?.subtitleCues?.length ? state.subtitleCues : subtitleOverride) || [];

  if (mode === "full") return cues;
  return cues.filter(c => (c.end ?? c.start) <= currentTime);
}

async function sendQuestion() {
  const q = document.getElementById("q");
  const mode = document.getElementById("mode").value;

  const question = (q.value || "").trim();
  if (!question) return;

  if (!pageState) {
    addMsg("assistant", "Open Netflix/YouTube and start playback first.");
    return;
  }

  addMsg("user", question);
  history.push({ role: "user", content: question });
  q.value = "";

  const seenCues = getSeenCues(pageState, mode);

  const payload = {
    platform: pageState.platform,
    title: pageState.title || "Unknown title",
    current_time: pageState.currentTime || 0,
    duration: pageState.duration || null,
    mode,
    question,
    subtitle_cues: seenCues,
    history: history.slice(-10)
  };

  try {
    const resp = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!resp.ok) {
      const t = await resp.text();
      throw new Error(`Backend error: ${resp.status} ${t}`);
    }
    const data = await resp.json();
    addMsg("assistant", data.answer, data.citations || []);
    history.push({ role: "assistant", content: data.answer });
  } catch (e) {
    addMsg("assistant", `Could not reach backend.\n\n${String(e)}\n\nMake sure backend is running on localhost:8000.`);
  }
}

document.getElementById("send").addEventListener("click", sendQuestion);
document.getElementById("q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendQuestion();
});

document.getElementById("subFile").addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;

  const text = await file.text();
  subtitleOverride = parseSrtOrVtt(text);

  const info = document.getElementById("subInfo");
  info.textContent = `Loaded ${subtitleOverride.length} subtitle cues from ${file.name}.`;
});

async function loop() {
  pageState = await requestPageState();
  updateUIFromState(pageState);
  setTimeout(loop, 1000);
}

loop();