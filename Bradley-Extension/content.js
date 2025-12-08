const BRADLEY_API = 'https://bradleyai.replit.app';
const SCAN_INTERVAL = 5000;
const CONFIDENCE_THRESHOLD = 0.85;

let isEnabled = true;
let scanQueue = [];
let isScanning = false;

chrome.storage.sync.get(['enabled'], (data) => {
  isEnabled = data.enabled !== false;
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.enabled) {
    isEnabled = changes.enabled.newValue;
    if (!isEnabled) {
      removeAllWarnings();
    }
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SHOW_WARNING') {
    showThreatWarning(message.data);
  }
});

function scanMedia() {
  if (!isEnabled) return;

  const videos = document.querySelectorAll('video');
  const audios = document.querySelectorAll('audio');

  [...videos, ...audios].forEach(media => {
    if (media.dataset.bradleyScanned) return;
    
    const url = media.src || media.currentSrc;
    if (!url || url.startsWith('blob:') || url.startsWith('data:')) {
      media.dataset.bradleyScanned = 'skipped';
      return;
    }

    media.dataset.bradleyScanned = 'pending';
    addScanIndicator(media);
    
    scanQueue.push({ element: media, url: url });
  });

  processQueue();
}

async function processQueue() {
  if (isScanning || scanQueue.length === 0) return;
  
  isScanning = true;
  
  while (scanQueue.length > 0) {
    const item = scanQueue.shift();
    await analyzeMedia(item.element, item.url);
  }
  
  isScanning = false;
}

async function analyzeMedia(element, url) {
  try {
    const mediaType = element.tagName.toLowerCase() === 'video' ? 'video' : 'audio';
    
    const response = await fetch(`${BRADLEY_API}/api/detect`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-Bradley-Extension': 'v0.2.0'
      },
      body: JSON.stringify({ 
        url: url,
        type: mediaType,
        page_url: window.location.href
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const result = await response.json();
    
    element.dataset.bradleyScanned = 'complete';
    element.dataset.bradleyResult = JSON.stringify(result);
    
    updateScanIndicator(element, result);
    
    chrome.runtime.sendMessage({ type: 'SCAN_COMPLETE' });

    if (result.is_deepfake && result.confidence > CONFIDENCE_THRESHOLD) {
      chrome.runtime.sendMessage({
        type: 'THREAT',
        data: {
          ...result,
          type: mediaType
        },
        url: window.location.href
      });
      
      showThreatWarning(result, element);
    }

  } catch (error) {
    console.log('[BRADLEY] Scan error:', error.message);
    element.dataset.bradleyScanned = 'error';
    updateScanIndicator(element, { error: true });
  }
}

function addScanIndicator(element) {
  const indicator = document.createElement('div');
  indicator.className = 'bradley-scan-indicator bradley-scanning';
  indicator.innerHTML = `
    <div class="bradley-icon">⟐</div>
    <span>Scanning...</span>
  `;
  
  const wrapper = document.createElement('div');
  wrapper.className = 'bradley-media-wrapper';
  wrapper.style.position = 'relative';
  wrapper.style.display = 'inline-block';
  
  element.parentNode.insertBefore(wrapper, element);
  wrapper.appendChild(element);
  wrapper.appendChild(indicator);
}

function updateScanIndicator(element, result) {
  const wrapper = element.closest('.bradley-media-wrapper');
  if (!wrapper) return;
  
  const indicator = wrapper.querySelector('.bradley-scan-indicator');
  if (!indicator) return;
  
  indicator.classList.remove('bradley-scanning');
  
  if (result.error) {
    indicator.classList.add('bradley-error');
    indicator.innerHTML = `
      <div class="bradley-icon">⚠</div>
      <span>Scan failed</span>
    `;
  } else if (result.is_deepfake && result.confidence > CONFIDENCE_THRESHOLD) {
    indicator.classList.add('bradley-threat');
    indicator.innerHTML = `
      <div class="bradley-icon">⚠</div>
      <span>THREAT: ${Math.round(result.confidence * 100)}%</span>
    `;
  } else {
    indicator.classList.add('bradley-safe');
    indicator.innerHTML = `
      <div class="bradley-icon">✓</div>
      <span>Verified</span>
    `;
    
    setTimeout(() => {
      indicator.style.opacity = '0';
      setTimeout(() => indicator.remove(), 300);
    }, 3000);
  }
}

function showThreatWarning(result, element = null) {
  const existingWarning = document.querySelector('.bradley-threat-overlay');
  if (existingWarning) return;
  
  const overlay = document.createElement('div');
  overlay.className = 'bradley-threat-overlay';
  overlay.innerHTML = `
    <div class="bradley-warning-box">
      <div class="bradley-warning-header">
        <span class="bradley-logo">⟐ BRADLEY AI</span>
        <button class="bradley-close">×</button>
      </div>
      <div class="bradley-warning-content">
        <h2>⚠ DEEPFAKE DETECTED</h2>
        <p class="bradley-confidence">Confidence: ${Math.round((result.confidence || 0.9) * 100)}%</p>
        <p class="bradley-message">
          This media appears to be synthetically generated or manipulated.
          Exercise caution with information from this source.
        </p>
        <div class="bradley-actions">
          <button class="bradley-btn bradley-btn-primary" id="bradley-dismiss">Acknowledge</button>
          <button class="bradley-btn bradley-btn-secondary" id="bradley-report">Report</button>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(overlay);
  
  overlay.querySelector('.bradley-close').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#bradley-dismiss').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#bradley-report').addEventListener('click', () => {
    window.open(`${BRADLEY_API}/report?url=${encodeURIComponent(window.location.href)}`, '_blank');
    overlay.remove();
  });
}

function removeAllWarnings() {
  document.querySelectorAll('.bradley-scan-indicator, .bradley-threat-overlay').forEach(el => el.remove());
}

scanMedia();
setInterval(scanMedia, SCAN_INTERVAL);

const observer = new MutationObserver((mutations) => {
  let shouldScan = false;
  mutations.forEach((mutation) => {
    if (mutation.addedNodes.length) {
      mutation.addedNodes.forEach((node) => {
        if (node.tagName === 'VIDEO' || node.tagName === 'AUDIO' || 
            (node.querySelectorAll && (node.querySelectorAll('video, audio').length > 0))) {
          shouldScan = true;
        }
      });
    }
  });
  if (shouldScan) scanMedia();
});

observer.observe(document.body, { childList: true, subtree: true });

console.log('[BRADLEY] Guardian active - scanning for threats');
