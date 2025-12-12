const API_BASE = 'https://bradley-ai.replit.app';
const MAX_THREAT_HISTORY = 100;
const MAX_NOTIFICATIONS_PER_MINUTE = 5;
const VALID_THREAT_TYPES = ['video', 'audio', 'deepfake', 'voice_clone', 'synthetic'];
const MAX_ATOMIC_RETRIES = 3;

class AsyncMutex {
  constructor() {
    this.queue = [];
    this.locked = false;
  }
  
  async acquire() {
    return new Promise((resolve) => {
      if (!this.locked) {
        this.locked = true;
        resolve();
      } else {
        this.queue.push(resolve);
      }
    });
  }
  
  release() {
    if (this.queue.length > 0) {
      const next = this.queue.shift();
      next();
    } else {
      this.locked = false;
    }
  }
  
  async withLock(fn) {
    await this.acquire();
    try {
      return await fn();
    } finally {
      this.release();
    }
  }
}

const storageMutex = new AsyncMutex();

async function atomicIncrement(storageArea, key, amount = 1) {
  return storageMutex.withLock(async () => {
    for (let attempt = 0; attempt < MAX_ATOMIC_RETRIES; attempt++) {
      try {
        const data = await storageArea.get([key]);
        const currentValue = data[key] || 0;
        const newValue = currentValue + amount;
        await storageArea.set({ [key]: newValue });
        return newValue;
      } catch (error) {
        if (attempt === MAX_ATOMIC_RETRIES - 1) {
          throw error;
        }
        await new Promise(r => setTimeout(r, 10 * (attempt + 1)));
      }
    }
  });
}

async function atomicUpdate(storageArea, updates) {
  return storageMutex.withLock(async () => {
    for (let attempt = 0; attempt < MAX_ATOMIC_RETRIES; attempt++) {
      try {
        const keys = Object.keys(updates);
        const data = await storageArea.get(keys);
        const newData = {};
        
        for (const key of keys) {
          const update = updates[key];
          if (typeof update === 'function') {
            newData[key] = update(data[key]);
          } else {
            newData[key] = update;
          }
        }
        
        await storageArea.set(newData);
        return newData;
      } catch (error) {
        if (attempt === MAX_ATOMIC_RETRIES - 1) {
          throw error;
        }
        await new Promise(r => setTimeout(r, 10 * (attempt + 1)));
      }
    }
  });
}

class NotificationRateLimiter {
  constructor(maxPerMinute = MAX_NOTIFICATIONS_PER_MINUTE) {
    this.notifications = [];
    this.maxPerMinute = maxPerMinute;
  }
  
  canSend() {
    const now = Date.now();
    this.notifications = this.notifications.filter(t => now - t < 60000);
    return this.notifications.length < this.maxPerMinute;
  }
  
  recordSent() {
    this.notifications.push(Date.now());
  }
}

const notificationLimiter = new NotificationRateLimiter();

function validateThreatData(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Invalid threat data: must be object');
  }
  
  if (typeof data.confidence !== 'number' || 
      !Number.isFinite(data.confidence) ||
      data.confidence < 0 || 
      data.confidence > 1) {
    throw new Error('Invalid confidence: must be number between 0 and 1');
  }
  
  if (data.type && !VALID_THREAT_TYPES.includes(data.type)) {
    throw new Error('Invalid threat type');
  }
  
  return true;
}

function validateUrl(url) {
  if (!url || typeof url !== 'string') {
    throw new Error('Invalid URL: must be string');
  }
  
  try {
    const parsed = new URL(url);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      throw new Error('Invalid URL protocol: must be http or https');
    }
    return true;
  } catch (e) {
    if (e.message.includes('Invalid URL')) {
      throw e;
    }
    throw new Error('Invalid URL format');
  }
}

function validateSender(sender) {
  if (!sender || !sender.tab) {
    return false;
  }
  
  if (!sender.url) {
    return false;
  }
  
  try {
    const url = new URL(sender.url);
    if (!['http:', 'https:'].includes(url.protocol)) {
      return false;
    }
  } catch {
    return false;
  }
  
  return true;
}

function sanitizeUrl(url) {
  try {
    const parsed = new URL(url);
    const sensitiveParams = ['token', 'key', 'session', 'auth', 'password', 'access_token', 'api_key', 'secret'];
    sensitiveParams.forEach(param => parsed.searchParams.delete(param));
    return parsed.toString();
  } catch {
    return '[Invalid URL]';
  }
}

function sanitizeUrlForDisplay(url) {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.length > 30 
      ? parsed.pathname.substring(0, 27) + '...' 
      : parsed.pathname;
    return `${parsed.hostname}${path}`;
  } catch {
    return '[Invalid URL]';
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  try {
    await chrome.storage.sync.set({ 
      enabled: true, 
      threats: 0,
      totalScans: 0,
      lastThreat: null
    });
    
    await chrome.storage.local.set({
      threatHistory: []
    });
    
    console.log('[BRADLEY] Guardian installed – protecting the grid');
  } catch (error) {
    console.error('[BRADLEY] Installation error:', error);
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message.type !== 'string') {
    sendResponse({ success: false, error: 'Invalid message format' });
    return;
  }
  
  if (message.type === 'THREAT') {
    if (!validateSender(sender)) {
      console.warn('[BRADLEY] Rejected threat from untrusted sender');
      sendResponse({ success: false, error: 'Untrusted sender' });
      return;
    }
    
    try {
      validateThreatData(message.data);
      validateUrl(message.url);
      handleThreatDetection(message.data, message.url, sender.tab)
        .then(() => sendResponse({ success: true }))
        .catch(err => sendResponse({ success: false, error: err.message }));
    } catch (error) {
      console.error('[BRADLEY] Threat validation error:', error.message);
      sendResponse({ success: false, error: error.message });
    }
    return true;
    
  } else if (message.type === 'SCAN_COMPLETE') {
    if (!validateSender(sender)) {
      sendResponse({ success: false, error: 'Untrusted sender' });
      return;
    }
    
    updateScanCount()
      .then(() => sendResponse({ success: true }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
    
  } else if (message.type === 'GET_STATUS') {
    chrome.storage.sync.get(['enabled', 'threats', 'totalScans'])
      .then(data => sendResponse({ success: true, data }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
    
  } else if (message.type === 'GET_HISTORY') {
    chrome.storage.local.get(['threatHistory'])
      .then(data => sendResponse({ success: true, history: data.threatHistory || [] }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
  
  sendResponse({ success: false, error: 'Unknown message type' });
});

async function handleThreatDetection(threatData, pageUrl, tab) {
  try {
    const sanitizedUrl = sanitizeUrl(pageUrl);
    const confidence = Math.min(1, Math.max(0, Number(threatData.confidence) || 0));
    
    const threatRecord = {
      url: sanitizedUrl,
      confidence: confidence,
      type: threatData.type || 'deepfake',
      timestamp: Date.now()
    };
    
    await atomicUpdate(chrome.storage.sync, {
      threats: (current) => (current || 0) + 1,
      lastThreat: threatRecord
    });
    
    await storeThreatHistory(threatRecord);
    await showThreatNotification(threatData, pageUrl);
    
    if (tab?.id) {
      try {
        await chrome.tabs.sendMessage(tab.id, {
          type: 'SHOW_WARNING',
          data: {
            confidence: confidence,
            type: threatData.type || 'deepfake'
          }
        });
      } catch (msgError) {
        console.warn('[BRADLEY] Failed to send warning to tab:', msgError.message);
      }
    }
  } catch (error) {
    console.error('[BRADLEY] Threat handling error:', error);
    throw error;
  }
}

async function storeThreatHistory(threat) {
  try {
    const data = await chrome.storage.local.get(['threatHistory']);
    const history = data.threatHistory || [];
    
    history.push(threat);
    
    if (history.length > MAX_THREAT_HISTORY) {
      history.shift();
    }
    
    await chrome.storage.local.set({ threatHistory: history });
  } catch (error) {
    console.error('[BRADLEY] Failed to store threat history:', error);
  }
}

async function showThreatNotification(threatData, pageUrl) {
  if (!notificationLimiter.canSend()) {
    console.warn('[BRADLEY] Notification rate limit reached');
    return;
  }
  
  try {
    const displayUrl = sanitizeUrlForDisplay(pageUrl);
    const confidence = Math.round(Math.min(100, Math.max(0, (threatData.confidence || 0) * 100)));
    
    await chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'Bradley AI - Threat Detected!',
      message: `Potential deepfake detected (${confidence}% confidence)\n${displayUrl}`,
      priority: 2
    });
    
    notificationLimiter.recordSent();
  } catch (error) {
    console.error('[BRADLEY] Notification error:', error);
  }
}

async function updateScanCount() {
  try {
    await atomicIncrement(chrome.storage.sync, 'totalScans', 1);
  } catch (error) {
    console.error('[BRADLEY] Failed to update scan count:', error);
    try {
      await atomicIncrement(chrome.storage.local, 'totalScans', 1);
    } catch (fallbackError) {
      console.error('[BRADLEY] Fallback storage failed:', fallbackError);
    }
  }
}

async function updateBadgeForAllTabs(enabled) {
  try {
    const tabs = await chrome.tabs.query({});
    
    for (const tab of tabs) {
      if (tab.id) {
        try {
          await chrome.action.setBadgeText({ 
            text: enabled ? '' : 'OFF',
            tabId: tab.id 
          });
          await chrome.action.setBadgeBackgroundColor({ 
            color: enabled ? '#00ff41' : '#ff0040',
            tabId: tab.id
          });
        } catch {
        }
      }
    }
  } catch (error) {
    console.error('[BRADLEY] Failed to update badges:', error);
  }
}

chrome.action.onClicked.addListener(async (tab) => {
  try {
    const data = await chrome.storage.sync.get(['enabled']);
    const newState = !data.enabled;
    await chrome.storage.sync.set({ enabled: newState });
    await updateBadgeForAllTabs(newState);
    
    console.log(`[BRADLEY] Protection ${newState ? 'enabled' : 'disabled'}`);
  } catch (error) {
    console.error('[BRADLEY] Failed to toggle extension:', error);
  }
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete') {
    try {
      const data = await chrome.storage.sync.get(['enabled']);
      await chrome.action.setBadgeText({ 
        text: data.enabled ? '' : 'OFF',
        tabId: tabId 
      });
      await chrome.action.setBadgeBackgroundColor({ 
        color: data.enabled ? '#00ff41' : '#ff0040',
        tabId: tabId
      });
    } catch {
    }
  }
});
