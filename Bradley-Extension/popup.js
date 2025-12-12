const API_BASE = 'https://bradleyai.replit.app';
const MAX_LOG_ENTRIES = 10;

function sanitizeText(str) {
  if (typeof str !== 'string') return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function sanitizeUrlForDisplay(url) {
  if (!url || typeof url !== 'string') return 'Unknown';
  try {
    const parsed = new URL(url);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return 'Unknown';
    }
    return parsed.hostname;
  } catch {
    return 'Unknown';
  }
}

function getElement(id) {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`[BRADLEY POPUP] Element not found: ${id}`);
  }
  return el;
}

function safeSetText(id, text) {
  const el = getElement(id);
  if (el) {
    el.textContent = String(text);
  }
}

function safeSetClass(id, className) {
  const el = getElement(id);
  if (el) {
    el.className = className;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await loadStatus();
    setupEventListeners();
    await loadThreatHistory();
  } catch (error) {
    console.error('[BRADLEY POPUP] Initialization error:', error);
    showError('Failed to initialize popup');
  }
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== 'sync') return;
  
  if (changes.enabled || changes.threats || changes.totalScans || changes.lastThreat) {
    loadStatus().catch(err => {
      console.error('[BRADLEY POPUP] Failed to reload status:', err);
    });
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || typeof msg.type !== 'string') {
    return;
  }
  
  if (msg.type === 'SHOW_WARNING' || msg.type === 'STATUS_UPDATE') {
    loadStatus().catch(err => {
      console.error('[BRADLEY POPUP] Failed to update status:', err);
    });
  }
});

async function loadStatus() {
  try {
    const data = await chrome.storage.sync.get(['enabled', 'threats', 'totalScans', 'lastThreat']);
    updateUI(data);
  } catch (error) {
    console.error('[BRADLEY POPUP] Storage error:', error);
    showError('Failed to load status');
  }
  
  try {
    const response = await fetch(`${API_BASE}/api/status`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000)
    });
    
    if (response.ok) {
      const serverStatus = await response.json();
      updateServerStatus(true, serverStatus);
    } else {
      updateServerStatus(false);
    }
  } catch (error) {
    console.warn('[BRADLEY POPUP] Server offline:', error.message);
    updateServerStatus(false);
  }
}

function updateServerStatus(online, data = null) {
  const serverIndicator = getElement('server-status');
  if (serverIndicator) {
    serverIndicator.textContent = online ? 'Grid: Online' : 'Grid: Offline';
    serverIndicator.className = online ? 'server-online' : 'server-offline';
  }
}

function updateUI(data) {
  const isEnabled = data.enabled !== false;
  
  const statusDot = getElement('status-dot');
  const statusText = getElement('status-text');
  const toggleText = getElement('toggle-text');
  
  if (statusDot) {
    statusDot.className = 'status-dot ' + (isEnabled ? 'online' : 'offline');
  }
  
  if (statusText) {
    statusText.textContent = isEnabled ? 'ONLINE' : 'OFFLINE';
    statusText.className = isEnabled ? 'online' : 'offline';
  }
  
  if (toggleText) {
    toggleText.textContent = isEnabled ? 'DISABLE PROTECTION' : 'ENABLE PROTECTION';
  }
  
  const threatCount = Number(data.threats) || 0;
  const scanCount = Number(data.totalScans) || 0;
  
  safeSetText('threats-count', threatCount);
  safeSetText('scans-count', scanCount);
  
  if (data.lastThreat && typeof data.lastThreat === 'object') {
    displayLastThreat(data.lastThreat);
  }
}

function displayLastThreat(threat) {
  const threatSection = getElement('last-threat');
  const threatUrl = getElement('threat-url');
  
  if (!threatSection || !threatUrl) return;
  
  threatSection.style.display = 'block';
  
  const hostname = sanitizeUrlForDisplay(threat.url);
  threatUrl.textContent = hostname;
  
  if (threat.url && typeof threat.url === 'string') {
    threatUrl.title = sanitizeText(threat.url);
  }
  
  const confidenceEl = getElement('threat-confidence');
  if (confidenceEl && typeof threat.confidence === 'number') {
    const confidence = Math.round(Math.min(100, Math.max(0, threat.confidence * 100)));
    confidenceEl.textContent = `${confidence}%`;
  }
}

async function loadThreatHistory() {
  try {
    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: 'GET_HISTORY' }, resolve);
    });
    
    if (response && response.success && Array.isArray(response.history)) {
      const log = getElement('threat-log');
      if (!log) return;
      
      log.innerHTML = '';
      
      const recentThreats = response.history.slice(-MAX_LOG_ENTRIES).reverse();
      
      recentThreats.forEach(threat => {
        if (threat && typeof threat === 'object') {
          addThreatEntry(threat);
        }
      });
    }
  } catch (error) {
    console.error('[BRADLEY POPUP] Failed to load threat history:', error);
  }
}

function addThreatEntry(threat) {
  const log = getElement('threat-log');
  if (!log) return;
  
  const entry = document.createElement('div');
  entry.className = 'threat-entry';
  
  const hostname = sanitizeUrlForDisplay(threat.url);
  const label = sanitizeText(threat.type || 'DEEPFAKE');
  const confidence = typeof threat.confidence === 'number' 
    ? Math.round(Math.min(100, Math.max(0, threat.confidence * 100))) 
    : 0;
  
  const timestamp = threat.timestamp 
    ? new Date(threat.timestamp).toLocaleTimeString() 
    : new Date().toLocaleTimeString();
  
  const strong = document.createElement('strong');
  strong.textContent = 'THREAT: ';
  
  const labelSpan = document.createElement('span');
  labelSpan.textContent = `${label} (${confidence}%)`;
  
  const br = document.createElement('br');
  
  const small = document.createElement('small');
  small.textContent = `${hostname} - ${timestamp}`;
  
  entry.appendChild(strong);
  entry.appendChild(labelSpan);
  entry.appendChild(br);
  entry.appendChild(small);
  
  log.prepend(entry);
  
  while (log.children.length > MAX_LOG_ENTRIES) {
    log.removeChild(log.lastChild);
  }
}

function setupEventListeners() {
  const toggleBtn = getElement('toggle-btn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', handleToggle);
  }
  
  const dashboardBtn = getElement('dashboard-btn');
  if (dashboardBtn) {
    dashboardBtn.addEventListener('click', () => {
      chrome.tabs.create({ url: API_BASE });
    });
  }
  
  const clearBtn = getElement('clear-log-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', handleClearLog);
  }
}

async function handleToggle() {
  try {
    const data = await chrome.storage.sync.get(['enabled']);
    const newState = data.enabled === false;
    
    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage({
        type: 'SET_ENABLED',
        enabled: newState
      }, resolve);
    });
    
    if (response && response.success) {
      await loadStatus();
    } else {
      throw new Error(response?.error || 'Toggle failed');
    }
  } catch (error) {
    console.error('[BRADLEY POPUP] Toggle error:', error);
    showError('Failed to toggle protection');
  }
}

async function handleClearLog() {
  try {
    const log = getElement('threat-log');
    if (log) {
      log.innerHTML = '';
    }
  } catch (error) {
    console.error('[BRADLEY POPUP] Clear log error:', error);
  }
}

function showError(message) {
  const errorEl = getElement('error-message');
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.style.display = 'block';
    setTimeout(() => {
      errorEl.style.display = 'none';
    }, 3000);
  }
}
