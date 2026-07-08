const saveButton = document.getElementById("save");
const statusEl = document.getElementById("status");
const backendUrlEl = document.getElementById("backendUrl");

function sendMessage(message) {
  return new Promise((resolve) => chrome.runtime.sendMessage(message, resolve));
}

async function loadSettings() {
  const response = await sendMessage({ type: "GET_LOOKUP_SETTINGS" });
  if (response?.backendUrl) backendUrlEl.value = response.backendUrl;
  await checkHealth();
}

async function checkHealth() {
  statusEl.textContent = "Checking";
  const response = await sendMessage({ type: "LOOKUP_HEALTH" });
  statusEl.textContent = response?.ok ? "Ready" : "Offline";
}

saveButton.addEventListener("click", async () => {
  const backendUrl = backendUrlEl.value.trim();
  const response = await sendMessage({ type: "SET_LOOKUP_SETTINGS", backendUrl });
  if (!response?.ok) {
    statusEl.textContent = "Save failed";
    return;
  }
  backendUrlEl.value = response.backendUrl;
  await checkHealth();
});

backendUrlEl.addEventListener("change", () => {
  statusEl.textContent = "Unsaved";
});

loadSettings().catch((error) => {
  statusEl.textContent = error.message || "Error";
});
