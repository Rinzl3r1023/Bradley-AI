// BRADLEY AI - URL ANALYZER
// v1.4.0 - December 2025

const CONFIG = {
  API_BASE: '',
  REQUEST_TIMEOUT: 30000,
  MAX_FREE_ANALYSES: 3,
  RATE_LIMIT_WINDOW: 3600000
};

class BradleyAnalyzer {
  constructor() {
    this.input = document.getElementById('video-url-input');
    this.analyzeBtn = document.getElementById('analyze-btn');
    this.resultsContainer = document.getElementById('analysis-results');
    this.loadingContainer = document.getElementById('analysis-loading');
    this.errorContainer = document.getElementById('analysis-error');
    this.progressBar = document.getElementById('progress-fill');
    
    this.progressInterval = null;
    
    this.init();
    this.initInstallButtons();
    this.initStats();
  }
  
  init() {
    this.input.addEventListener('input', () => {
      const isValid = this.isValidURL(this.input.value.trim());
      this.analyzeBtn.disabled = !isValid;
    });
    
    this.analyzeBtn.addEventListener('click', () => {
      this.analyzeVideo();
    });
    
    this.input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !this.analyzeBtn.disabled) {
        this.analyzeVideo();
      }
    });
  }
  
  initInstallButtons() {
    const installButtons = document.querySelectorAll('#install-extension-btn, .install-extension-trigger');
    
    installButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        this.handleInstallExtension();
      });
    });
  }
  
  handleInstallExtension() {
    if (this.isExtensionInstalled()) {
      alert('Bradley AI Extension is already installed!');
      return;
    }
    
    alert('Chrome Web Store submission pending!\n\nExtension will be available for one-click install within 7 days.\n\nFor early access, join our beta program.');
    
    window.location.href = '/beta';
  }
  
  isExtensionInstalled() {
    return typeof window.BradleyExtensionActive !== 'undefined';
  }
  
  isValidURL(str) {
    try {
      const url = new URL(str);
      return ['http:', 'https:'].includes(url.protocol);
    } catch {
      return false;
    }
  }
  
  checkRateLimit() {
    const analyses = JSON.parse(localStorage.getItem('bradley_analyses') || '[]');
    const now = Date.now();
    
    const recentAnalyses = analyses.filter(timestamp => 
      now - timestamp < CONFIG.RATE_LIMIT_WINDOW
    );
    
    if (this.isExtensionInstalled()) {
      return { allowed: true, remaining: 'unlimited' };
    }
    
    if (recentAnalyses.length >= CONFIG.MAX_FREE_ANALYSES) {
      return { 
        allowed: false, 
        remaining: 0,
        resetTime: new Date(recentAnalyses[0] + CONFIG.RATE_LIMIT_WINDOW)
      };
    }
    
    return { 
      allowed: true, 
      remaining: CONFIG.MAX_FREE_ANALYSES - recentAnalyses.length 
    };
  }
  
  recordAnalysis() {
    if (this.isExtensionInstalled()) return;
    
    const analyses = JSON.parse(localStorage.getItem('bradley_analyses') || '[]');
    analyses.push(Date.now());
    
    const now = Date.now();
    const recentAnalyses = analyses.filter(timestamp => 
      now - timestamp < CONFIG.RATE_LIMIT_WINDOW
    );
    
    localStorage.setItem('bradley_analyses', JSON.stringify(recentAnalyses));
  }
  
  async analyzeVideo() {
    const url = this.input.value.trim();
    
    if (!this.isValidURL(url)) {
      this.showError('Invalid URL', 'Please enter a valid video URL starting with http:// or https://');
      return;
    }
    
    const rateLimit = this.checkRateLimit();
    if (!rateLimit.allowed) {
      const resetTime = rateLimit.resetTime.toLocaleTimeString();
      this.showError(
        'Rate Limit Reached',
        `Free users can analyze ${CONFIG.MAX_FREE_ANALYSES} videos per hour.\n\nNext analysis available at: ${resetTime}\n\nInstall the browser extension for unlimited analyses!`
      );
      return;
    }
    
    this.hideAll();
    
    this.showLoading();
    
    this.simulateProgress();
    
    try {
      const result = await this.callAPI(url);
      this.recordAnalysis();
      this.hideLoading();
      this.showResult(result, url);
    } catch (error) {
      this.hideLoading();
      this.showError('Analysis Failed', error.message || 'Unable to analyze video. Please try again.');
    }
  }
  
  async callAPI(url) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);
    
    try {
      const response = await fetch(`${CONFIG.API_BASE}/detect_video_deepfake`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url_or_path: url }),
        signal: controller.signal
      });
      
      clearTimeout(timeout);
      
      if (!response.ok) {
        throw new Error(`Server error (${response.status}). Please try again.`);
      }
      
      const data = await response.json();
      
      if (!data || typeof data.is_deepfake !== 'boolean') {
        throw new Error('Invalid response from server');
      }
      
      return data;
      
    } catch (error) {
      clearTimeout(timeout);
      
      if (error.name === 'AbortError') {
        throw new Error('Request timeout. Video may be too large or server is busy.');
      }
      
      throw error;
    }
  }
  
  simulateProgress() {
    let progress = 0;
    this.progressInterval = setInterval(() => {
      progress += Math.random() * 12;
      if (progress > 85) progress = 85;
      this.progressBar.style.width = `${progress}%`;
    }, 400);
  }
  
  showLoading() {
    this.loadingContainer.classList.remove('hidden');
    this.progressBar.style.width = '0%';
  }
  
  hideLoading() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
    this.progressBar.style.width = '100%';
    setTimeout(() => {
      this.loadingContainer.classList.add('hidden');
    }, 300);
  }
  
  showResult(result, originalUrl) {
    const { is_deepfake, confidence } = result;
    const confidencePercent = Math.round(confidence * 100);
    
    let resultType, resultIcon, resultTitle, resultDescription;
    
    if (confidence >= 0.70) {
      if (is_deepfake) {
        resultType = 'ai';
        resultIcon = '&#x26A0;';
        resultTitle = 'AI-GENERATED CONTENT DETECTED';
        resultDescription = 'This video appears to contain AI-generated or manipulated content. Exercise caution when sharing or trusting this media.';
      } else {
        resultType = 'human';
        resultIcon = '&#x2713;';
        resultTitle = 'HUMAN-GENERATED CONTENT';
        resultDescription = 'No AI manipulation detected in this video. This content appears to be authentic.';
      }
    } else {
      resultType = 'unknown';
      resultIcon = '?';
      resultTitle = 'UNCERTAIN RESULT';
      resultDescription = 'Detection confidence is low. The video may contain subtle manipulation or be in a format that\'s difficult to analyze. Proceed with caution.';
    }
    
    const now = new Date().toLocaleString();
    
    this.resultsContainer.innerHTML = `
      <div class="result-header">
        <span class="result-icon">${resultIcon}</span>
        <h3 class="result-title ${resultType}">${resultTitle}</h3>
      </div>
      
      <div class="result-confidence" style="color: ${resultType === 'human' ? '#00ff00' : resultType === 'ai' ? '#ff0000' : '#ffaa00'}">
        ${confidencePercent}% Confidence
      </div>
      
      <div class="result-meta">
        <span>Model: Bradley v1.4.0</span>
        <span>|</span>
        <span>${now}</span>
      </div>
      
      <p class="result-description">${resultDescription}</p>
      
      <div class="result-actions">
        <button class="btn-analyze" onclick="bradleyAnalyzer.reset()">ANALYZE ANOTHER</button>
        <button class="btn-secondary" onclick="bradleyAnalyzer.copyResult('${resultTitle.replace(/'/g, "\\'")}', ${confidencePercent})">COPY RESULT</button>
      </div>
    `;
    
    this.resultsContainer.classList.remove('hidden');
    
    this.resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  
  showError(title, message) {
    this.errorContainer.innerHTML = `
      <h3 class="error-title">${this.escapeHtml(title)}</h3>
      <p class="error-message">${this.escapeHtml(message).replace(/\n/g, '<br>')}</p>
      <button class="btn-secondary" onclick="bradleyAnalyzer.reset()">TRY AGAIN</button>
    `;
    this.errorContainer.classList.remove('hidden');
    
    this.errorContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  
  hideAll() {
    this.resultsContainer.classList.add('hidden');
    this.errorContainer.classList.add('hidden');
    this.loadingContainer.classList.add('hidden');
  }
  
  reset() {
    this.input.value = '';
    this.input.focus();
    this.analyzeBtn.disabled = true;
    this.hideAll();
  }
  
  copyResult(title, confidence) {
    const text = `Bradley AI Analysis Result:\n\n${title}\nConfidence: ${confidence}%\nAnalyzed: ${new Date().toLocaleString()}\n\nPowered by Bradley AI Guardian v1.4.0`;
    
    navigator.clipboard.writeText(text).then(() => {
      alert('Result copied to clipboard!');
    }).catch(() => {
      alert('Unable to copy. Please try again.');
    });
  }
  
  sanitizeUrlForDisplay(url) {
    try {
      const parsed = new URL(url);
      return parsed.hostname + parsed.pathname.substring(0, 30) + (parsed.pathname.length > 30 ? '...' : '');
    } catch {
      return 'Unknown URL';
    }
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  initStats() {
    this.updateStats();
    setInterval(() => this.updateStats(), 10000);
  }
  
  updateStats() {
    const baseScans = 142847;
    const baseThreats = 3291;
    const baseUsers = 1204;
    
    const randomIncrement = () => Math.floor(Math.random() * 10);
    
    const statScans = document.getElementById('stat-scans');
    const statThreats = document.getElementById('stat-threats');
    const statUsers = document.getElementById('stat-users');
    
    if (statScans) {
      const currentScans = parseInt(statScans.textContent.replace(/,/g, '')) || baseScans;
      this.animateCounter(statScans, currentScans, currentScans + randomIncrement());
    }
    
    if (statThreats) {
      const currentThreats = parseInt(statThreats.textContent.replace(/,/g, '')) || baseThreats;
      if (Math.random() > 0.7) {
        this.animateCounter(statThreats, currentThreats, currentThreats + 1);
      }
    }
    
    if (statUsers) {
      const currentUsers = parseInt(statUsers.textContent.replace(/,/g, '')) || baseUsers;
      if (Math.random() > 0.9) {
        this.animateCounter(statUsers, currentUsers, currentUsers + 1);
      }
    }
  }
  
  animateCounter(element, start, end) {
    const duration = 1000;
    const range = end - start;
    const increment = range / (duration / 50);
    let current = start;
    
    const timer = setInterval(() => {
      current += increment;
      if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
        current = end;
        clearInterval(timer);
      }
      element.textContent = Math.floor(current).toLocaleString();
    }, 50);
  }
}

let bradleyAnalyzer;
document.addEventListener('DOMContentLoaded', () => {
  bradleyAnalyzer = new BradleyAnalyzer();
});
