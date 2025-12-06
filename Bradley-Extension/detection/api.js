const BRADLEY_API_BASE = 'https://bradley-ai.replit.app';

export async function detectDeepfake(mediaUrl, type = 'video') {
  try {
    const response = await fetch(`${BRADLEY_API_BASE}/api/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Bradley-Extension': 'v0.2.0'
      },
      body: JSON.stringify({
        url: mediaUrl,
        type: type
      })
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[BRADLEY API] Detection error:', error);
    return {
      error: true,
      message: error.message,
      is_deepfake: false,
      confidence: 0
    };
  }
}

export async function getServerStatus() {
  try {
    const response = await fetch(`${BRADLEY_API_BASE}/api/status`);
    if (!response.ok) {
      throw new Error('Server unavailable');
    }
    return await response.json();
  } catch (error) {
    return {
      status: 'offline',
      error: error.message
    };
  }
}

export async function reportThreat(threatData) {
  try {
    const response = await fetch(`${BRADLEY_API_BASE}/api/report`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(threatData)
    });
    
    return await response.json();
  } catch (error) {
    console.error('[BRADLEY API] Report error:', error);
    return { success: false, error: error.message };
  }
}
