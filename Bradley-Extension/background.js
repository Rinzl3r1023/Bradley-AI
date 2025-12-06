const API_BASE = 'https://bradley-ai.replit.app';

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ 
    enabled: true, 
    threats: 0,
    totalScans: 0,
    lastThreat: null
  });
  console.log('[BRADLEY] Guardian installed – protecting the grid');
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'THREAT') {
    handleThreatDetection(message.data, message.url, sender.tab);
  } else if (message.type === 'SCAN_COMPLETE') {
    updateScanCount();
  } else if (message.type === 'GET_STATUS') {
    chrome.storage.sync.get(['enabled', 'threats', 'totalScans'], (data) => {
      sendResponse(data);
    });
    return true;
  }
});

async function handleThreatDetection(threatData, pageUrl, tab) {
  chrome.storage.sync.get(['threats'], (data) => {
    const newCount = (data.threats || 0) + 1;
    chrome.storage.sync.set({ 
      threats: newCount,
      lastThreat: {
        url: pageUrl,
        confidence: threatData.confidence,
        type: threatData.type || 'deepfake',
        timestamp: Date.now()
      }
    });
  });

  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title: 'Bradley AI - Threat Detected!',
    message: `Potential deepfake detected (${Math.round(threatData.confidence * 100)}% confidence)\n${pageUrl}`,
    priority: 2
  });

  if (tab && tab.id) {
    chrome.tabs.sendMessage(tab.id, {
      type: 'SHOW_WARNING',
      data: threatData
    });
  }
}

function updateScanCount() {
  chrome.storage.sync.get(['totalScans'], (data) => {
    chrome.storage.sync.set({ totalScans: (data.totalScans || 0) + 1 });
  });
}

chrome.action.onClicked.addListener((tab) => {
  chrome.storage.sync.get(['enabled'], (data) => {
    const newState = !data.enabled;
    chrome.storage.sync.set({ enabled: newState });
    
    chrome.action.setBadgeText({ 
      text: newState ? '' : 'OFF',
      tabId: tab.id 
    });
    chrome.action.setBadgeBackgroundColor({ 
      color: newState ? '#00ff00' : '#ff0000' 
    });
  });
});
