let state = {
  ok: false,
  platform: "netflix",
  title: "",
  currentTime: 0,
  duration: null,
  subtitleCues: [],
  error: ""
};

function findVideo() {
  return document.querySelector("video");
}

function guessTitle() {
  // Netflix changes markup; try multiple places
  const t1 = document.querySelector("[data-uia='video-title']")?.textContent?.trim();
  if (t1) return t1;

  // Some pages include title in document.title
  const dt = document.title?.trim();
  if (dt) return dt;

  return "Netflix Title (unknown)";
}

function tick() {
  const video = findVideo();
  if (!video) {
    state.ok = false;
    state.error = "No <video> found (start playback).";
    return;
  }

  state.ok = true;
  state.error = "";
  state.title = guessTitle();
  state.currentTime = video.currentTime || 0;
  state.duration = (isFinite(video.duration) && video.duration > 0) ? video.duration : null;

  // Subtitle capture not implemented for Netflix MVP
  state.subtitleCues = [];
}

setInterval(tick, 750);

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "GET_STATE") {
    sendResponse(state);
  }
});