let state = {
  ok: false,
  platform: "youtube",
  title: "",
  currentTime: 0,
  duration: null,
  subtitleCues: [],
  error: ""
};

function getVideo() {
  return document.querySelector("video");
}

function getTitle() {
  // YouTube title is dynamic; keep best-effort
  const h1 = document.querySelector("h1.ytd-watch-metadata");
  const t = h1?.innerText?.trim();
  if (t) return t;
  return document.title.replace(" - YouTube", "").trim();
}

function captureCaptionText() {
  // Visible captions appear in ytp-caption-segment
  const segs = Array.from(document.querySelectorAll(".ytp-caption-segment"));
  const text = segs.map(s => s.textContent?.trim()).filter(Boolean).join(" ").trim();
  return text;
}

let lastCaption = "";
let lastCaptionTime = 0;

function tick() {
  const video = getVideo();
  if (!video) {
    state.ok = false;
    state.error = "No <video> found (open a YouTube video).";
    return;
  }

  state.ok = true;
  state.error = "";
  state.title = getTitle();
  state.currentTime = video.currentTime || 0;
  state.duration = (isFinite(video.duration) && video.duration > 0) ? video.duration : null;

  const cap = captureCaptionText();

  // Record cue when caption changes and is non-empty
  if (cap && cap !== lastCaption) {
    const now = state.currentTime;
    // close previous cue
    if (lastCaption && state.subtitleCues.length) {
      state.subtitleCues[state.subtitleCues.length - 1].end = now;
    }
    state.subtitleCues.push({
      start: now,
      end: now + 2.0, // provisional, updated next change
      text: cap
    });
    lastCaption = cap;
    lastCaptionTime = now;

    // Keep memory bounded
    if (state.subtitleCues.length > 800) {
      state.subtitleCues = state.subtitleCues.slice(-800);
    }
  } else if (lastCaption && state.subtitleCues.length) {
    // Extend last cue end slightly
    const now = state.currentTime;
    state.subtitleCues[state.subtitleCues.length - 1].end = Math.max(now, state.subtitleCues[state.subtitleCues.length - 1].end);
  }
}

setInterval(tick, 500);

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "GET_STATE") {
    sendResponse(state);
  }
});