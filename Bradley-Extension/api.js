const BRADLEY_API_BASE = 'https://bradleyai.replit.app';
const REQUEST_TIMEOUT = 30000;
const MAX_RETRIES = 2;

function validateMediaUrl(url) {
  try {
    const parsed = new URL(url);
    
    if (parsed.protocol !== 'https:') {
      throw new Error('Only HTTPS URLs are allowed');
    }
    
    const blockedPatterns = [
      /^(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)/i,
      /\.(local|internal|corp)$/i
    ];
    
    for (const pattern of blockedPatterns) {
      if (pattern.test(parsed.hostname)) {
        throw new Error('Blocked URL pattern');
      }
    }
    
    return true;
  } catch (error) {
    throw new Error(`Invalid URL: ${error.message}`);
  }
}

function sanitizeUrl(url) {
  try {
    const parsed = new URL(url);
    const sensitiveParams = ['token', 'key', 'session', 'auth', 'password', 'access_token', 'api_key', 'secret'];
    sensitiveParams.forEach(param => parsed.searchParams.delete(param));
    return parsed.toString();
  } catch {
    return url;
  }
}

async function fetchWithTimeout(url, options = {}, timeout = REQUEST_TIMEOUT) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
}

async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetchWithTimeout(url, options);
      
      if (response.status >= 400 && response.status < 500) {
        return response;
      }
      
      if (response.ok) {
        return response;
      }
      
      if (attempt < retries) {
        const delay = Math.pow(2, attempt) * 1000;
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      return response;
    } catch (error) {
      if (attempt < retries) {
        const delay = Math.pow(2, attempt) * 1000;
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      throw error;
    }
  }
}

export async function detectDeepfake(mediaUrl, type = 'video') {
  if (!mediaUrl || typeof mediaUrl !== 'string') {
    return { success: false, error: 'Invalid media URL' };
  }
  
  if (!['video', 'audio'].includes(type)) {
    return { success: false, error: 'Type must be "video" or "audio"' };
  }
  
  try {
    validateMediaUrl(mediaUrl);
  } catch (error) {
    return { success: false, error: error.message };
  }
  
  const sanitizedUrl = sanitizeUrl(mediaUrl);
  const endpoint = type === 'video' 
    ? `${BRADLEY_API_BASE}/detect_video_deepfake`
    : `${BRADLEY_API_BASE}/detect_audio_deepfake`;
  
  try {
    const response = await fetchWithRetry(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url_or_path: sanitizedUrl })
    });
    
    if (!response.ok) {
      return { success: false, error: `API request failed: ${response.status}` };
    }
    
    const data = await response.json();
    
    if (typeof data.is_deepfake !== 'boolean') {
      return { success: false, error: 'Invalid API response format' };
    }
    
    return {
      success: true,
      is_deepfake: data.is_deepfake,
      confidence: data.confidence || 0,
      analysis: data.analysis || {},
      model: data.model || 'unknown'
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

export async function getServerStatus() {
  try {
    const response = await fetchWithTimeout(`${BRADLEY_API_BASE}/api/status`);
    
    if (!response.ok) {
      return { success: false, error: `Status check failed: ${response.status}` };
    }
    
    const data = await response.json();
    return { success: true, ...data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

export async function reportThreat(threatData) {
  if (!threatData || typeof threatData !== 'object') {
    return { success: false, error: 'Invalid threat data' };
  }
  
  const sanitizedData = {
    pageUrl: sanitizeUrl(threatData.pageUrl || ''),
    confidence: Number(threatData.confidence) || 0,
    timestamp: Date.now(),
    userAgent: navigator.userAgent,
    extensionVersion: '1.2.0'
  };
  
  try {
    const response = await fetchWithRetry(`${BRADLEY_API_BASE}/api/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sanitizedData)
    });
    
    if (!response.ok) {
      return { success: false, error: `Report failed: ${response.status}` };
    }
    
    const data = await response.json();
    return { success: true, ...data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

export async function detectDeepfakeBatch(items, maxBatchSize = 5) {
  if (!Array.isArray(items)) {
    return { success: false, error: 'Items must be an array' };
  }
  
  const batch = items.slice(0, maxBatchSize);
  const results = await Promise.all(
    batch.map(item => detectDeepfake(item.url, item.type))
  );
  
  return {
    success: true,
    results,
    processed: results.length,
    total: items.length
  };
}

export { validateMediaUrl, sanitizeUrl, fetchWithTimeout, fetchWithRetry };
