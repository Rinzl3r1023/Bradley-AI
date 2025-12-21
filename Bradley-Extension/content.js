const CONFIG = {
  API_BASE: 'https://bradleyai.replit.app',
  SCAN_INTERVAL: 30000,
  CONFIDENCE_THRESHOLD: 0.70,  // Industry standard for AI detection
  MAX_RETRIES: 2,
  REQUEST_TIMEOUT: 15000,
  RATE_LIMIT_WINDOW: 60000,
  RATE_LIMIT_MAX: 20,
  MAX_QUEUE_SIZE: 15,
  MAX_CACHED_URLS: 500,
  DEBOUNCE_DELAY: 300
};

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

class ExtensionState {
  constructor() {
    this.isEnabled = true;
    this.hasConsent = false;
    this.scanQueue = [];
    this.isScanning = false;
    this.scannedUrls = new Map();
    this.rateLimitCounter = [];
  }
  async initialize() {
    const data = await chrome.storage.sync.get(['enabled', 'hasConsent']);
    this.isEnabled = data.enabled !== false;
    this.hasConsent = data.hasConsent === true;
    if (!this.hasConsent) this.showConsentDialog();
  }
  isRateLimited() {
    const now = Date.now();
    this.rateLimitCounter = this.rateLimitCounter.filter(t => now - t < CONFIG.RATE_LIMIT_WINDOW);
    return this.rateLimitCounter.length >= CONFIG.RATE_LIMIT_MAX;
  }
  recordRequest() { this.rateLimitCounter.push(Date.now()); }
  hasScannedUrl(url) { return this.scannedUrls.has(url); }
  markScanned(url) {
    if (this.scannedUrls.size >= CONFIG.MAX_CACHED_URLS) {
      const first = this.scannedUrls.keys().next().value;
      this.scannedUrls.delete(first);
    }
    this.scannedUrls.set(url, Date.now());
  }
  showConsentDialog() { new ConsentDialog().show(accepted => {
    this.hasConsent = accepted;
    chrome.storage.sync.set({ hasConsent: accepted });
    if (accepted && scanner) scanner.scan();
  }); }
}

const state = new ExtensionState();

class URLValidator {
  static ALLOWED_PROTOCOLS = ['https:'];
  static BLOCKED_PATTERNS = [
    /^(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)/i,
    /\.(local|internal|corp)$/i
  ];
  static isValid(urlString) {
    try {
      const url = new URL(urlString);
      if (!this.ALLOWED_PROTOCOLS.includes(url.protocol)) return false;
      for (const pattern of this.BLOCKED_PATTERNS) if (pattern.test(url.hostname)) return false;
      return true;
    } catch { return false; }
  }
  static sanitize(urlString) {
    try {
      const url = new URL(urlString);
      const sensitive = ['token','key','session','auth','password','access_token','api_key','secret'];
      sensitive.forEach(p => url.searchParams.delete(p));
      return url.toString();
    } catch { return null; }
  }
}

class BradleyAPIClient {
  async analyzeMedia(url, mediaType, retries = 0) {
    if (!URLValidator.isValid(url)) throw new Error('Invalid URL');
    const sanitized = URLValidator.sanitize(url);
    if (state.isRateLimited()) throw new Error('Rate limited');
    const endpoint = mediaType === 'video'
      ? `${CONFIG.API_BASE}/detect_video_deepfake`
      : `${CONFIG.API_BASE}/detect_audio_deepfake`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);
    try {
      state.recordRequest();
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url_or_path: sanitized }),
        signal: controller.signal
      });
      clearTimeout(timeout);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      if (!result || typeof result.is_deepfake !== 'boolean') throw new Error('Invalid response');
      return result;
    } catch (error) {
      clearTimeout(timeout);
      if (retries < CONFIG.MAX_RETRIES && error.name !== 'AbortError') {
        await new Promise(r => setTimeout(r, Math.pow(2, retries) * 1000));
        return this.analyzeMedia(url, mediaType, retries + 1);
      }
      throw error;
    }
  }
}

class MediaScanner {
  constructor() { this.apiClient = new BradleyAPIClient(); }
  scan() {
    console.log('[BRADLEY] Scan triggered. Enabled:', state.isEnabled, 'Consent:', state.hasConsent);
    if (!state.isEnabled || !state.hasConsent) return;
    const medias = [...document.querySelectorAll('video, audio')];
    console.log('[BRADLEY] Found media elements:', medias.length);
    medias.forEach(media => {
      if (media.dataset.bradleyScanned) return;
      const url = media.src || media.currentSrc;
      if (!url || url.startsWith('blob:') || url.startsWith('data:')) {
        media.dataset.bradleyScanned = 'skipped';
        return;
      }
      if (state.hasScannedUrl(url)) {
        media.dataset.bradleyScanned = 'duplicate';
        return;
      }
      if (state.scanQueue.length >= CONFIG.MAX_QUEUE_SIZE) return;
      media.dataset.bradleyScanned = 'pending';
      state.markScanned(url);
      const indicator = new ScanIndicator(media);
      indicator.showScanning();
      state.scanQueue.push({ element: media, url, indicator });
    });
    this.processQueue();
  }
  async processQueue() {
    if (state.isScanning || state.scanQueue.length === 0) return;
    state.isScanning = true;
    while (state.scanQueue.length > 0) {
      const item = state.scanQueue.shift();
      await this.analyzeMedia(item);
    }
    state.isScanning = false;
  }
  async analyzeMedia(item) {
    const { element, url, indicator } = item;
    const mediaType = element.tagName.toLowerCase() === 'video' ? 'video' : 'audio';
    try {
      const result = await this.apiClient.analyzeMedia(url, mediaType);
      element.dataset.bradleyScanned = 'complete';
      indicator.showResult(result);
      chrome.runtime.sendMessage({
        type: 'SCAN_COMPLETE',
        data: { url, result }
      }).catch(err => console.error('[BRADLEY] Message failed:', err));
      if (result.is_deepfake && result.confidence > CONFIG.CONFIDENCE_THRESHOLD) {
        chrome.runtime.sendMessage({
          type: 'THREAT',
          data: { 
            confidence: result.confidence,
            type: mediaType === 'video' ? 'deepfake' : 'voice_clone'
          },
          url: url
        }).catch(err => console.error('[BRADLEY] Message failed:', err));
        new ThreatWarning(result).show();
      }
    } catch (error) {
      element.dataset.bradleyScanned = 'error';
      indicator.showError(error.message || 'Scan failed');
    }
  }
}

class ScanIndicator {
  constructor(el) { this.el = el; this.overlay = null; }
  showScanning() { this.render('bradley-scanning', '⟐', 'Scanning...'); }
  showResult(r) {
    const confidencePercent = Math.round(r.confidence * 100);
    
    // High confidence detection (>= 70%)
    if (r.confidence >= CONFIG.CONFIDENCE_THRESHOLD) {
      if (r.is_deepfake) {
        // AI-Generated - persist warning (don't auto-remove)
        this.render('bradley-fake', '⚠', `AI-Generated (${confidencePercent}%)`);
      } else {
        // Human-Generated - fade after 3 seconds
        this.render('bradley-real', '✓', `Human-Generated (${confidencePercent}%)`);
        setTimeout(() => this.remove(), 3000);
      }
    } else {
      // Low confidence - uncertain result
      this.render('bradley-uncertain', '?', `Unknown (${confidencePercent}%)`);
      setTimeout(() => this.remove(), 5000); // Longer display than success
    }
  }
  showError(msg) { this.render('bradley-error', '⚠', msg); }
  render(cls, icon, text) {
    if (!this.overlay) this.createOverlay();
    this.overlay.className = `bradley-indicator ${cls}`;
    this.overlay.innerHTML = '';
    
    const i = document.createElement('div'); 
    i.className = 'bradley-icon'; 
    i.textContent = icon;
    
    const t = document.createElement('span'); 
    t.textContent = text;
    
    this.overlay.appendChild(i); 
    this.overlay.appendChild(t);
    
    // Add dismiss button for persistent warnings (AI-Generated)
    if (cls === 'bradley-fake') {
      const dismissBtn = document.createElement('button');
      dismissBtn.className = 'bradley-dismiss-btn';
      dismissBtn.textContent = '×';
      dismissBtn.title = 'Dismiss warning';
      dismissBtn.onclick = (e) => {
        e.stopPropagation();
        this.remove();
      };
      this.overlay.appendChild(dismissBtn);
    }
  }
  createOverlay() {
    console.log('[BRADLEY] Creating overlay for:', this.el.tagName, this.el.src?.substring(0, 50));
    
    this.overlay = document.createElement('div');
    this.overlay.className = 'bradley-indicator bradley-scanning';
    
    // Video/audio elements cannot have visible children - we need a wrapper
    let container = this.el.parentElement;
    
    // If parent is body or has no positioning, create a wrapper
    if (!container || container === document.body || container.tagName === 'HTML') {
      const wrapper = document.createElement('div');
      wrapper.className = 'bradley-media-wrapper';
      wrapper.style.cssText = 'position:relative;display:inline-block;';
      this.el.parentNode.insertBefore(wrapper, this.el);
      wrapper.appendChild(this.el);
      container = wrapper;
    } else {
      // Ensure parent has relative positioning for absolute overlay
      const computedPosition = getComputedStyle(container).position;
      if (computedPosition === 'static') {
        container.style.position = 'relative';
      }
    }
    
    // Append overlay to the container (not the video itself)
    container.appendChild(this.overlay);
    console.log('[BRADLEY] Overlay appended to:', container.tagName, container.className);
  }
  remove() {
    if (this.overlay) {
      this.overlay.style.opacity = '0';
      setTimeout(() => this.overlay && this.overlay.remove(), 300);
    }
  }
}

class ThreatWarning {
  constructor(result) { this.result = result; }
  show() {
    if (document.querySelector('.bradley-threat-overlay')) return;
   
    const overlay = document.createElement('div');
    overlay.className = 'bradley-threat-overlay';
    overlay.setAttribute('role', 'alertdialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'bradley-warning-title');
   
    const box = document.createElement('div');
    box.className = 'bradley-warning-box';
   
    const header = document.createElement('div');
    header.className = 'bradley-warning-header';
   
    const logo = document.createElement('span');
    logo.className = 'bradley-logo';
    logo.textContent = '⟐ BRADLEY AI';
   
    const closeBtn = document.createElement('button');
    closeBtn.className = 'bradley-close';
    closeBtn.textContent = '×';
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.onclick = () => overlay.remove();
   
    header.appendChild(logo);
    header.appendChild(closeBtn);
   
    const content = document.createElement('div');
    content.className = 'bradley-warning-content';
   
    const title = document.createElement('h2');
    title.id = 'bradley-warning-title';
    title.textContent = '⚠ DEEPFAKE DETECTED';
   
    const confidence = document.createElement('p');
    confidence.className = 'bradley-confidence';
    confidence.textContent = `Confidence: ${Math.round(this.result.confidence * 100)}%`;
   
    const message = document.createElement('p');
    message.className = 'bradley-message';
    message.textContent = 'This media appears to be synthetically generated or manipulated.';
   
    const actions = document.createElement('div');
    actions.className = 'bradley-actions';
   
    const dismissBtn = document.createElement('button');
    dismissBtn.className = 'bradley-btn bradley-btn-primary';
    dismissBtn.id = 'bradley-dismiss';
    dismissBtn.textContent = 'Acknowledge';
    dismissBtn.onclick = () => overlay.remove();
   
    const reportBtn = document.createElement('button');
    reportBtn.className = 'bradley-btn bradley-btn-secondary';
    reportBtn.textContent = 'Report';
    reportBtn.onclick = () => {
      chrome.runtime.sendMessage({
        type: 'REPORT_THREAT',
        data: { pageUrl: location.href, confidence: this.result.confidence }
      }).catch(err => console.error('[BRADLEY] Report failed:', err));
      overlay.remove();
    };
   
    actions.appendChild(dismissBtn);
    actions.appendChild(reportBtn);
   
    content.appendChild(title);
    content.appendChild(confidence);
    content.appendChild(message);
    content.appendChild(actions);
   
    box.appendChild(header);
    box.appendChild(content);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
   
    dismissBtn.focus();
   
    overlay.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') overlay.remove();
    });
  }
}

class ConsentDialog {
  show(callback) {
    const dialog = document.createElement('div');
    dialog.className = 'bradley-consent-overlay';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
   
    const box = document.createElement('div');
    box.className = 'bradley-consent-box';
   
    const header = document.createElement('div');
    header.className = 'bradley-consent-header';
   
    const logo = document.createElement('span');
    logo.className = 'bradley-logo';
    logo.textContent = '⟐ BRADLEY AI';
   
    header.appendChild(logo);
   
    const content = document.createElement('div');
    content.className = 'bradley-consent-content';
   
    const title = document.createElement('h2');
    title.textContent = 'Privacy & Consent';
   
    const intro = document.createElement('p');
    intro.textContent = 'Bradley AI scans media on web pages to detect deepfakes and protect you from synthetic content.';
   
    const collectHeader = document.createElement('p');
    const collectStrong = document.createElement('strong');
    collectStrong.textContent = 'What we collect:';
    collectHeader.appendChild(collectStrong);
   
    const collectList = document.createElement('ul');
    ['URLs of media files (videos/audio) on pages you visit', 'Detection results for threat analysis'].forEach(text => {
      const li = document.createElement('li');
      li.textContent = text;
      collectList.appendChild(li);
    });
   
    const dontCollectHeader = document.createElement('p');
    const dontCollectStrong = document.createElement('strong');
    dontCollectStrong.textContent = "What we don't collect:";
    dontCollectHeader.appendChild(dontCollectStrong);
   
    const dontCollectList = document.createElement('ul');
    ['Your personal information', 'Browsing history', 'Passwords or sensitive data'].forEach(text => {
      const li = document.createElement('li');
      li.textContent = text;
      dontCollectList.appendChild(li);
    });
   
    const actions = document.createElement('div');
    actions.className = 'bradley-consent-actions';
   
    const acceptBtn = document.createElement('button');
    acceptBtn.className = 'bradley-btn bradley-btn-primary';
    acceptBtn.id = 'consent-accept';
    acceptBtn.textContent = 'Accept & Enable';
    acceptBtn.onclick = () => { dialog.remove(); callback(true); };
   
    const declineBtn = document.createElement('button');
    declineBtn.className = 'bradley-btn bradley-btn-secondary';
    declineBtn.id = 'consent-decline';
    declineBtn.textContent = 'Decline';
    declineBtn.onclick = () => { dialog.remove(); callback(false); };
   
    actions.appendChild(acceptBtn);
    actions.appendChild(declineBtn);
   
    content.appendChild(title);
    content.appendChild(intro);
    content.appendChild(collectHeader);
    content.appendChild(collectList);
    content.appendChild(dontCollectHeader);
    content.appendChild(dontCollectList);
    content.appendChild(actions);
   
    box.appendChild(header);
    box.appendChild(content);
    dialog.appendChild(box);
    document.body.appendChild(dialog);
   
    acceptBtn.focus();
   
    dialog.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        dialog.remove();
        callback(false);
      }
    });
  }
}

let scanner;
state.initialize().then(() => {
  scanner = new MediaScanner();
  if (state.hasConsent && state.isEnabled) {
    scanner.scan();
    setInterval(() => scanner.scan(), CONFIG.SCAN_INTERVAL);
  }
  const debounced = debounce(() => state.hasConsent && state.isEnabled && scanner.scan(), 300);
  const observer = new MutationObserver(() => debounced());
  observer.observe(document.body, { childList: true, subtree: true });
});
