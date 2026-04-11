const API_SERVER = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", () => {
  const statusEl = document.getElementById("status");
  const urlListEl = document.getElementById("urlList");
  const refreshBtn = document.getElementById("refreshBtn");
  
  let capturedUrls = [];
  let selectedUrl = null;
  
  async function fetchUrls() {
    try {
      const res = await fetch(`${API_SERVER}/urls`);
      const data = await res.json();
      capturedUrls = data.urls || [];
      renderUrls();
    } catch (e) {
      statusEl.textContent = "Cannot connect to API server";
      statusEl.className = "status waiting";
    }
  }
  
  async function selectUrl(url) {
    try {
      const res = await fetch(`${API_SERVER}/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      if (data.status === "ok") {
        selectedUrl = url;
        renderUrls();
        statusEl.textContent = "Selected! Python will download...";
        statusEl.className = "status listening";
      }
    } catch (e) {
      console.error(e);
    }
  }
  
  function renderUrls() {
    urlListEl.innerHTML = "";
    
    if (capturedUrls.length === 0) {
      statusEl.textContent = "No URLs captured yet. Play a video.";
      statusEl.className = "status waiting";
      return;
    }
    
    statusEl.textContent = `${capturedUrls.length} URL(s) captured`;
    statusEl.className = "status listening";
    
    capturedUrls.forEach((item) => {
      const li = document.createElement("li");
      const isSelected = item.url === selectedUrl;
      li.className = isSelected ? "selected" : "";
      
      li.innerHTML = `
        <span class="type">${item.type}</span>
        <div class="url">${item.url}</div>
      `;
      
      const btn = document.createElement("button");
      btn.className = "select";
      btn.textContent = isSelected ? "✓ Selected" : "Select to Download";
      btn.disabled = isSelected;
      btn.onclick = () => selectUrl(item.url);
      
      li.appendChild(btn);
      urlListEl.appendChild(li);
    });
  }
  
  refreshBtn.addEventListener("click", fetchUrls);
  
  fetchUrls();
  setInterval(fetchUrls, 2000);
});