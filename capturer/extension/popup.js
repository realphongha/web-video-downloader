const API_SERVER = "http://127.0.0.1:5000";
const DOWNLOAD_ENDPOINT = `${API_SERVER}/download`;

document.addEventListener("DOMContentLoaded", () => {
  const statusEl = document.getElementById("status");
  const statusTextEl = document.getElementById("statusText");
  const captureToggleEl = document.getElementById("captureToggle");
  const clearBtnEl = document.getElementById("clearBtn");
  const reloadBtnEl = document.getElementById("reloadBtn");
  const urlListEl = document.getElementById("urlList");
  
  let capturedUrls = [];
  
  function formatTime(timestamp) {
    const d = new Date(timestamp);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  
  async function loadUrls() {
    const result = await chrome.storage.local.get(["capturedUrls"]);
    capturedUrls = result.capturedUrls || [];
    renderUrls();
  }
  
  async function loadStatus() {
    const result = await chrome.storage.local.get(["isCapturing"]);
    const isCapturing = result.isCapturing || false;
    captureToggleEl.checked = isCapturing;
    updateStatusUI(isCapturing);
  }
  
  function updateStatusUI(isCapturing) {
    if (isCapturing) {
      statusEl.className = "status on";
      statusTextEl.textContent = "Capturing: ON";
    } else {
      statusEl.className = "status off";
      statusTextEl.textContent = "Capturing: OFF";
    }
  }
  
  async function renderUrls() {
    urlListEl.innerHTML = "";
    
    if (capturedUrls.length === 0) {
      const li = document.createElement("li");
      li.innerHTML = `<div class="url" style="color: #6b7280;">No URLs captured. Turn ON capturing, then play video.</div>`;
      urlListEl.appendChild(li);
      return;
    }
    
    capturedUrls.forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <div class="header">
          <span class="type">${item.type}</span>
          <span class="time">${formatTime(item.timestamp)}</span>
        </div>
        <div class="url">${item.url}</div>
      `;
      
      const btn = document.createElement("button");
      btn.className = "select";
      btn.textContent = "Select to Download";
      btn.onclick = () => selectUrl(item.url);
      
      li.appendChild(btn);
      urlListEl.appendChild(li);
    });
  }
  
  async function selectUrl(url) {
    const item = capturedUrls.find(u => u.url === url);
    if (!item) return;
    
    try {
      const res = await fetch(DOWNLOAD_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: item.url,
          type: item.type,
          headers: item.headers
        })
      });
      const data = await res.json();
      if (data.status === "ok") {
        statusTextEl.textContent = "Selected! Download started...";
      }
    } catch (e) {
      console.error(e);
    }
  }
  
  captureToggleEl.addEventListener("change", async () => {
    const enabled = captureToggleEl.checked;
    await chrome.runtime.sendMessage({ action: "toggleCapturing", enabled });
    updateStatusUI(enabled);
  });
  
  clearBtnEl.addEventListener("click", async () => {
    await chrome.storage.local.set({ capturedUrls: [] });
    capturedUrls = [];
    renderUrls();
  });
  
  reloadBtnEl.addEventListener("click", async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      chrome.tabs.reload(tab.id);
    }
  });
  
  loadStatus();
  loadUrls();
  setInterval(loadUrls, 1000);
});