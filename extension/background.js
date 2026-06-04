chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id) return;

  try {
    await chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_SPOILER_SAFE_PANEL" });
  } catch (error) {
    console.error("Failed to toggle Spoiler Safe panel:", error);
  }
});