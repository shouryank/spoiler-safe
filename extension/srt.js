// Minimal SRT/VTT parser -> cues: {start, end, text}
function timeToSeconds(t) {
  // supports "00:01:02,500" or "00:01:02.500" or "01:02.500"
  const s = t.trim().replace(",", ".");
  const parts = s.split(":").map(p => p.trim());
  let sec = 0;
  if (parts.length === 3) {
    sec += parseFloat(parts[2]);
    sec += parseInt(parts[1], 10) * 60;
    sec += parseInt(parts[0], 10) * 3600;
  } else if (parts.length === 2) {
    sec += parseFloat(parts[1]);
    sec += parseInt(parts[0], 10) * 60;
  } else {
    sec = parseFloat(parts[0]);
  }
  return isNaN(sec) ? 0 : sec;
}

function parseSrtOrVtt(text) {
  const lines = text.replace(/\r/g, "").split("\n");
  const cues = [];
  let i = 0;

  // Skip WEBVTT header if present
  if (lines[0] && lines[0].startsWith("WEBVTT")) i++;

  while (i < lines.length) {
    // skip empty
    while (i < lines.length && lines[i].trim() === "") i++;
    if (i >= lines.length) break;

    // Optional numeric index
    if (/^\d+$/.test(lines[i].trim())) i++;

    // time line
    const timeLine = (lines[i] || "").trim();
    const m = timeLine.match(/(.+?)\s*-->\s*(.+?)(\s+.*)?$/);
    if (!m) { i++; continue; }

    const start = timeToSeconds(m[1]);
    const end = timeToSeconds(m[2]);
    i++;

    // text lines until blank
    const textLines = [];
    while (i < lines.length && lines[i].trim() !== "") {
      textLines.push(lines[i].trim());
      i++;
    }

    const cueText = textLines.join(" ").replace(/<[^>]+>/g, "").trim();
    if (cueText) cues.push({ start, end, text: cueText });

    i++;
  }

  return cues;
}