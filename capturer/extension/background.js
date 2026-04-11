const API_SERVER = "http://127.0.0.1:5000";
const CAPTURE_ENDPOINT = `${API_SERVER}/capture`;

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
const capturedUrls = new Map();

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    pageUrl = tab.url;
    capturedUrls.clear();
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

function processRequest(details) {
  const url = details.url;
  const responseHeaders = details.responseHeaders || [];
  const headers = {};
  
  for (const header of responseHeaders) {
    headers[header.name.toLowerCase()] = header.value;
  }
  
  const contentType = headers["content-type"] || "";
  const mediaType = isVideoUrl(url, contentType);
  
  if (mediaType && !capturedUrls.has(url)) {
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
    
    capturedUrls.set(url, {
      type: mediaType,
      headers: filteredHeaders,
    });
    
    sendToAPI(url, mediaType, filteredHeaders);
  }
}

chrome.webRequest.onCompleted.addListener(
  processRequest,
  { urls: ["<all_urls>"] }
);

chrome.webRequest.onErrorOccurred.addListener(
  processRequest,
  { urls: ["<all_urls>"] }
);

async function sendToAPI(url, streamType, headers) {
  try {
    const response = await fetch(CAPTURE_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: url,
        type: streamType,
        headers: headers,
      }),
    });
    
    const result = await response.json();
    console.log("[+] Sent to API server:", result);
  } catch (error) {
    console.error("[-] Failed to send to API server:", error);
  }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getCapturedUrls") {
    const urls = Array.from(capturedUrls.entries()).map(([url, data]) => ({
      url,
      type: data.type,
      headers: data.headers,
    }));
    sendResponse({ urls });
  }
  return true;
});