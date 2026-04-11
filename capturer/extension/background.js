const blacklist = new Set([
  "host",
  "content-length",
  "accept-encoding",
  "connection",
  "sec-ch-ua",
  "sec-ch-ua-mobile",
  "sec-ch-ua-platform",
  "sec-fetch-site",
  "sec-fetch-mode",
  "sec-fetch-dest",
]);

let pageUrl = null;
let isCapturing = false;

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    pageUrl = tab.url;
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "toggleCapturing") {
    isCapturing = request.enabled;
    chrome.storage.local.set({ isCapturing: isCapturing });
    if (isCapturing) {
      registerListeners();
    } else {
      unregisterListeners();
    }
    sendResponse({ isCapturing });
  } else if (request.action === "getStatus") {
    sendResponse({ isCapturing });
  } else if (request.action === "clearUrls") {
    chrome.storage.local.set({ capturedUrls: [] });
    sendResponse({ status: "ok" });
  }
  return true;
});

function registerListeners() {
  chrome.webRequest.onCompleted.addListener(
    processRequest,
    { urls: ["<all_urls>"] }
  );
  chrome.webRequest.onErrorOccurred.addListener(
    processRequest,
    { urls: ["<all_urls>"] }
  );
  console.log("[*] Capturing started");
}

function unregisterListeners() {
  chrome.webRequest.onCompleted.removeListener(processRequest);
  chrome.webRequest.onErrorOccurred.removeListener(processRequest);
  console.log("[*] Capturing stopped");
}

chrome.storage.local.get(["capturedUrls", "isCapturing"]).then((result) => {
  isCapturing = result.isCapturing || false;
  if (isCapturing) {
    registerListeners();
  }
});

function isVideoUrl(url, contentType) {
  if (url.includes(".m3u8")) return "hls";
  if (url.includes(".mpd")) return "dash";
  if (url.match(/\.(mp4|webm|mkv)(\?|$)/)) return "progressive";
  if (contentType.includes("application/vnd.apple.mpegurl") || contentType.includes("application/x-mpegurl")) return "hls";
  if (contentType.includes("application/dash+xml")) return "dash";
  if (contentType.includes("video/")) return "progressive";
  return null;
}

async function processRequest(details) {
  if (!isCapturing) return;
  
  const url = details.url;
  const responseHeaders = details.responseHeaders || [];
  const headers = {};
  
  for (const header of responseHeaders) {
    headers[header.name.toLowerCase()] = header.value;
  }
  
  const contentType = headers["content-type"] || "";
  const mediaType = isVideoUrl(url, contentType);
  
  if (!mediaType) return;
  
  const result = await chrome.storage.local.get(["capturedUrls"]);
  const capturedUrls = result.capturedUrls || [];
  
  if (capturedUrls.some(u => u.url === url)) return;
  
  console.log(`[+] Found ${mediaType}: ${url}`);
  
  const filteredHeaders = {};
  for (const [key, value] of Object.entries(headers)) {
    if (!blacklist.has(key)) {
      filteredHeaders[key] = value;
    }
  }
  
  if (pageUrl) {
    filteredHeaders["referer"] = pageUrl;
  }
  if (!filteredHeaders["user-agent"]) {
    filteredHeaders["user-agent"] = "Mozilla/5.0";
  }
  
  const newItem = {
    url,
    type: mediaType,
    headers: filteredHeaders,
    timestamp: Date.now()
  };
  
  capturedUrls.unshift(newItem);
  
  await chrome.storage.local.set({ capturedUrls });
}