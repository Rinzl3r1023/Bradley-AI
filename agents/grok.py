import os
import json
from typing import Dict, Optional

try:
    from openai import OpenAI
    GROK_AVAILABLE = True
except ImportError:
    GROK_AVAILABLE = False
    OpenAI = None


def get_grok_client():
    if not GROK_AVAILABLE:
        return None
    
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return None
    
    return OpenAI(base_url="https://api.x.ai/v1", api_key=api_key)


def analyze_threat_with_grok(threat_data: Dict) -> Optional[Dict]:
    client = get_grok_client()
    if not client:
        return None
    
    try:
        prompt = f"""Analyze this potential deepfake/AI-generated threat detection result and provide a security assessment:

Video Detection Result:
- Is Deepfake: {threat_data.get('video_result', {}).get('is_deepfake', 'N/A')}
- Confidence: {threat_data.get('video_result', {}).get('confidence', 'N/A')}

Audio Detection Result:  
- Is Voice Clone: {threat_data.get('audio_result', {}).get('is_deepfake', 'N/A')}
- Confidence: {threat_data.get('audio_result', {}).get('confidence', 'N/A')}

Provide a JSON response with:
- threat_assessment: Brief summary of the threat level
- recommended_action: What the user should do
- risk_score: 1-10 rating
- explanation: Technical explanation of the detection"""

        response = client.chat.completions.create(
            model="grok-2-1212",
            messages=[
                {
                    "role": "system",
                    "content": "You are Bradley AI, a cybersecurity guardian that protects users from deepfakes, voice clones, and synthetic identity fraud. Provide concise, actionable security assessments."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=500
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        print(f"[GROK] Analysis error: {e}")
        return None


def get_grok_status() -> Dict:
    client = get_grok_client()
    return {
        "available": GROK_AVAILABLE,
        "configured": client is not None,
        "model": "grok-2-1212" if client else None
    }
