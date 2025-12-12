import requests
import urllib.parse
import socket
import ipaddress
import logging
import os
import tempfile
import numpy as np
from typing import Dict, Any, Optional
import torch

logging.basicConfig(level=logging.INFO)

ALLOWED_DOMAINS = ['huggingface.co', 'cdn.huggingface.co', 'example.com']
ALLOWED_SCHEMES = ['https', 'http']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_REDIRECTS = 5

VOICE_ENCODER = None
REFERENCE_EMBEDDINGS = {}


def get_voice_encoder():
    global VOICE_ENCODER
    if VOICE_ENCODER is None:
        try:
            from resemblyzer import VoiceEncoder
            VOICE_ENCODER = VoiceEncoder()
            logging.info("Resemblyzer VoiceEncoder loaded")
        except Exception as e:
            logging.error(f"Failed to load VoiceEncoder: {e}")
    return VOICE_ENCODER


def is_allowed_domain(hostname: str) -> bool:
    return any(domain in hostname for domain in ALLOWED_DOMAINS)


def is_allowed_scheme(scheme: str) -> bool:
    return scheme in ALLOWED_SCHEMES


def resolve_and_validate_ip(hostname: str, scheme: str) -> bool:
    if not is_allowed_scheme(scheme):
        return False
    
    try:
        addrs = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for addr in addrs:
            ip_str = addr[4][0]
            if isinstance(ip_str, tuple):
                ip_str = ip_str[0]
            ip_str = ip_str.strip('[]')
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_multicast or ip.is_link_local or ip.is_reserved:
                return False
        return True
    except (socket.gaierror, ValueError):
        return False


def safe_request(url: str) -> Dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname
    scheme = parsed.scheme
    
    if not hostname:
        raise ValueError("Invalid URL: no hostname")
    
    if not is_allowed_domain(hostname):
        raise ValueError(f"Domain not allowed: {hostname}")
    
    if not is_allowed_scheme(scheme):
        raise ValueError(f"Scheme not allowed: {scheme}")
    
    if not resolve_and_validate_ip(hostname, scheme):
        raise ValueError(f"Invalid IP resolution for {hostname}")
    
    session = requests.Session()
    session.max_redirects = MAX_REDIRECTS
    
    try:
        response = session.get(url, allow_redirects=True, timeout=10, stream=True)
        response.raise_for_status()
        
        content = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            content.extend(chunk)
            if len(content) > MAX_FILE_SIZE:
                raise ValueError("File exceeded size limit during download")
        
        return {
            'status_code': response.status_code,
            'content': bytes(content),
            'headers': dict(response.headers)
        }
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Request failed: {e}")


def safe_file_path(path: str) -> str:
    base_dir = os.getcwd()
    real_base = os.path.realpath(base_dir)
    real_path = os.path.realpath(path)
    
    try:
        common = os.path.commonpath([real_base, real_path])
        if not common.startswith(real_base):
            raise ValueError(f"Path traversal attempt: {path}")
    except ValueError:
        raise ValueError(f"Path traversal attempt: {path}")
    
    return real_path


def download_and_save_audio(url: str) -> str:
    temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
    os.close(temp_fd)
    
    try:
        response = safe_request(url)
        if response['status_code'] != 200:
            raise ValueError(f"HTTP {response['status_code']}: {url}")
        
        with open(temp_path, 'wb') as f:
            f.write(response['content'])
        
        return temp_path
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def analyze_with_resemblyzer(audio_path: str) -> Dict[str, Any]:
    try:
        from resemblyzer import preprocess_wav
        
        encoder = get_voice_encoder()
        if encoder is None:
            return {'error': 'VoiceEncoder not available', 'is_deepfake': False, 'confidence': 0.5}
        
        wav = preprocess_wav(audio_path)
        embedding = encoder.embed_utterance(wav)
        
        embedding_std = np.std(embedding)
        embedding_mean = np.abs(np.mean(embedding))
        embedding_max = np.max(np.abs(embedding))
        
        anomaly_score = 0.0
        
        if embedding_std < 0.15:
            anomaly_score += 0.3
        
        if embedding_max > 0.8:
            anomaly_score += 0.2
        
        if embedding_mean < 0.05:
            anomaly_score += 0.2
        
        zero_crossings = np.sum(np.diff(np.sign(embedding)) != 0)
        if zero_crossings < len(embedding) * 0.3:
            anomaly_score += 0.3
        
        is_fake = anomaly_score > 0.5
        confidence = min(anomaly_score, 1.0) if is_fake else max(1.0 - anomaly_score, 0.0)
        
        return {
            'is_deepfake': is_fake,
            'confidence': round(confidence, 3),
            'label': 'FAKE' if is_fake else 'REAL',
            'details': {
                'embedding_std': round(float(embedding_std), 4),
                'embedding_mean': round(float(embedding_mean), 4),
                'anomaly_score': round(anomaly_score, 3),
                'method': 'resemblyzer_voice_embedding'
            }
        }
    except Exception as e:
        logging.error(f"Resemblyzer analysis failed: {e}")
        return {'error': str(e), 'is_deepfake': False, 'confidence': 0.5}


def detect_audio_deepfake(url_or_path: str) -> Dict[str, Any]:
    temp_path = None
    
    try:
        if url_or_path.startswith("http"):
            temp_path = download_and_save_audio(url_or_path)
            audio_input = temp_path
        else:
            audio_input = safe_file_path(url_or_path)
            if not os.path.isfile(audio_input):
                raise ValueError("File not found")
        
        result = analyze_with_resemblyzer(audio_input)
        return result
    
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        return {"error": str(e), "is_deepfake": False, "confidence": 0.0}
    except Exception as e:
        logging.critical(f"Unexpected error: {e}")
        return {"error": "Processing failed", "is_deepfake": False, "confidence": 0.0}
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


if __name__ == "__main__":
    test_url = "https://huggingface.co/datasets/huggingface/deepfake-detection/resolve/main/sample_real.wav"
    result = detect_audio_deepfake(test_url)
    print(result)
