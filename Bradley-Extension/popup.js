const API_BASE = 'https://bradley-ai.replit.app';

document.addEventListener('DOMContentLoaded', () => {
  loadStatus();
  setupEventListeners();
});

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
      const newState = !data.enabled;
      chrome.storage.sync.set({ enabled: newState }, () => {
        loadStatus();
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
