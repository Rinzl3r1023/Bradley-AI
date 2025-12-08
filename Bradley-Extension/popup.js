const API_BASE = 'https://bradleyai.replit.app';

document.addEventListener('DOMContentLoaded', () => {
  loadStatus();
  setupEventListeners();
  loadThreatLog();
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "THREAT") {
    const countEl = document.getElementById('threats-count');
    const count = parseInt(countEl.textContent) + 1;
    countEl.textContent = count;
    
    chrome.action.setBadgeText({text: count.toString()});
    chrome.action.setBadgeBackgroundColor({color: '#ff0000'});
    
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'Bradley AI — THREAT DETECTED',
      message: `Deepfake confidence: ${(msg.data.confidence*100).toFixed(1)}% on ${msg.url}`
    });
    
    addThreatEntry(msg.data, msg.url);
    
    chrome.storage.sync.get(['threats'], (data) => {
      chrome.storage.sync.set({ threats: (data.threats || 0) + 1 });
    });
  }
  
  if (msg.type === "SCAN_COMPLETE") {
    const scansEl = document.getElementById('scans-count');
    scansEl.textContent = parseInt(scansEl.textContent) + 1;
    
    chrome.storage.sync.get(['totalScans'], (data) => {
      chrome.storage.sync.set({ totalScans: (data.totalScans || 0) + 1 });
    });
  }
});

function addThreatEntry(data, url) {
  const log = document.getElementById('threat-log');
  const entry = document.createElement('div');
  entry.className = 'threat-entry';
  
  let hostname = 'Unknown';
  try {
    hostname = new URL(url).hostname;
  } catch {}
  
  entry.innerHTML = `
    <strong>THREAT:</strong> ${data.label || 'FAKE'} (${(data.confidence*100).toFixed(1)}%)
    <br><small>${hostname} - ${new Date().toLocaleTimeString()}</small>
  `;
  log.prepend(entry);
  
  while (log.children.length > 10) {
    log.removeChild(log.lastChild);
  }
}

function loadThreatLog() {
  chrome.storage.sync.get(['threatLog'], (data) => {
    const log = data.threatLog || [];
    log.forEach(item => {
      addThreatEntry(item.data, item.url);
    });
  });
}

function loadStatus() {
  chrome.storage.sync.get(['enabled', 'threats', 'totalScans', 'lastThreat'], (data) => {
    updateUI(data);
  });
  
  fetch(`${API_BASE}/api/status`)
    .then(r => r.json())
    .then(serverStatus => {
      console.log('[BRADLEY] Server status:', serverStatus);
    })
    .catch(err => {
      console.log('[BRADLEY] Server offline:', err.message);
    });
}

function updateUI(data) {
  const isEnabled = data.enabled !== false;
  
  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const toggleText = document.getElementById('toggle-text');
  
  statusDot.className = 'status-dot ' + (isEnabled ? 'online' : 'offline');
  statusText.textContent = isEnabled ? 'ONLINE' : 'OFFLINE';
  statusText.className = isEnabled ? 'online' : 'offline';
  toggleText.textContent = isEnabled ? 'DISABLE PROTECTION' : 'ENABLE PROTECTION';
  
  document.getElementById('threats-count').textContent = data.threats || 0;
  document.getElementById('scans-count').textContent = data.totalScans || 0;
  
  if (data.threats > 0) {
    chrome.action.setBadgeText({text: data.threats.toString()});
    chrome.action.setBadgeBackgroundColor({color: '#ff0000'});
  }
  
  if (data.lastThreat) {
    const threatSection = document.getElementById('last-threat');
    const threatUrl = document.getElementById('threat-url');
    threatSection.style.display = 'block';
    
    try {
      const url = new URL(data.lastThreat.url);
      threatUrl.textContent = url.hostname;
      threatUrl.title = data.lastThreat.url;
    } catch {
      threatUrl.textContent = 'Unknown';
    }
  }
}

function setupEventListeners() {
  document.getElementById('toggle-btn').addEventListener('click', () => {
    chrome.storage.sync.get(['enabled'], (data) => {
      const newState = data.enabled === false ? true : false;
      chrome.storage.sync.set({ enabled: newState }, () => {
        loadStatus();
        
        if (newState) {
          chrome.action.setBadgeText({text: ''});
        }
      });
    });
  });
  
  document.getElementById('dashboard-btn').addEventListener('click', () => {
    chrome.tabs.create({ url: API_BASE });
  });
}

chrome.storage.onChanged.addListener((changes) => {
  if (changes.enabled || changes.threats || changes.totalScans) {
    chrome.storage.sync.get(['enabled', 'threats', 'totalScans', 'lastThreat'], updateUI);
  }
});
