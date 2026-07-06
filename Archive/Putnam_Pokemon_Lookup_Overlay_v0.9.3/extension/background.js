const DEFAULT_BACKEND_URL = "http://127.0.0.1:8790";

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(["backendUrl"], (items) => {
    if (!items.backendUrl) {
      chrome.storage.local.set({ backendUrl: DEFAULT_BACKEND_URL });
    }
  });
});

function normalizeBackendUrl(value) {
  const raw = String(value || DEFAULT_BACKEND_URL).trim().replace(/\/+$/, "");
  return raw || DEFAULT_BACKEND_URL;
}

async function getBackendUrl() {
  const items = await chrome.storage.local.get(["backendUrl"]);
  return normalizeBackendUrl(items.backendUrl);
}

async function fetchJson(path, params) {
  const backendUrl = await getBackendUrl();
  const url = new URL(`${backendUrl}${path}`);
  for (const [key, value] of Object.entries(params || {})) {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      url.searchParams.set(key, String(value).trim());
    }
  }

  const response = await fetch(url.toString(), { cache: "no-store" });
  if (!response.ok) throw new Error(`Lookup server returned ${response.status}`);
  return response.json();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_LOOKUP_SETTINGS") {
    chrome.storage.local.get(["backendUrl"], (items) => {
      sendResponse({ ok: true, backendUrl: normalizeBackendUrl(items.backendUrl) });
    });
    return true;
  }

  if (message.type === "SET_LOOKUP_SETTINGS") {
    const backendUrl = normalizeBackendUrl(message.backendUrl);
    chrome.storage.local.set({ backendUrl }, () => {
      sendResponse({ ok: true, backendUrl });
    });
    return true;
  }

  if (message.type === "LOOKUP_HEALTH") {
    fetchJson("/api/health")
      .then((payload) => sendResponse({ ok: true, payload }))
      .catch((error) => sendResponse({ ok: false, error: error.message || "Lookup server offline" }));
    return true;
  }

  if (message.type === "OVERLAY_SEARCH") {
    fetchJson("/api/search", {
      q: message.query,
      set: message.setQuery,
      number: message.numberQuery,
      conditions: message.conditions || "NM,LP",
      include_images: "1",
      include_prices: "1"
    })
      .then((payload) => sendResponse({ ok: true, results: payload.results || [], backendUrl: payload.backendUrl }))
      .catch((error) => {
        sendResponse({
          ok: false,
          error: error.message || "Search failed. Is start_watcher_backend.bat running?"
        });
      });
    return true;
  }

  return false;
});
