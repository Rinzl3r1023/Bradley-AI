import requests
import urllib.parse
import socket
import ipaddress
import logging
import os
import tempfile
from threading import Lock
from typing import Optional, Dict, Any
import torch
from transformers import pipeline

logging.basicConfig(level=logging.INFO)

ALLOWED_DOMAINS = ["huggingface.co", "cdn.huggingface.co"]
ALLOWED_SCHEMES = ["https"]
MAX_REDIRECTS = 5
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

_encoder = None
_encoder_lock = Lock()


def is_allowed_domain(hostname: str) -> bool:
    hostname = hostname.lower()
    return any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in ALLOWED_DOMAINS
    )


def is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return (
            addr.is_private or
            addr.is_loopback or
            addr.is_link_local or
            addr.is_multicast or
            addr.is_reserved or
            (addr.version == 4 and 100 << 24 <= int(addr) <= 103 << 24)  # CGNAT
        )
    except ValueError:
        return True


def validate_url(url: str) -> Optional[str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return None
    hostname = parsed.hostname
    if not hostname or not is_allowed_domain(hostname):
        return None

    try:
        for addr in socket.getaddrinfo(hostname, None):
            ip = addr[4][0]
            if is_private_ip(ip):
                return None
    except Exception:
        return None
    return url


def safe_request(url: str, depth: int = 0) -> requests.Response:
    if depth > MAX_REDIRECTS:
        raise ValueError("Too many redirects")
    if not validate_url(url):
        raise ValueError(f"Disallowed URL: {url}")

    response = requests.get(url, allow_redirects=False, timeout=15, stream=True)
    
    if response.is_redirect:
        location = response.headers.get("Location")
        if location:
            next_url = urllib.parse.urljoin(url, location)
            return safe_request(next_url, depth + 1)
    
    response.raise_for_status()
    return response


def safe_audio_download(url: str) -> str:
    response = safe_request(url)
    total = 0
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                total += len(chunk)
                if total > MAX_FILE_SIZE:
                    raise ValueError("File too large")
                f.write(chunk)
        return path
    except Exception:
        if os.path.exists(path):
            os.unlink(path)
        raise


def safe_file_path(path: str) -> str:
    base_dir = os.path.realpath(os.getcwd())
    real_path = os.path.realpath(path)
    if not real_path.startswith(base_dir + os.sep):
        raise ValueError(f"Path traversal attempt: {path}")
    return real_path


def get_deepfake_detector():
    global _encoder
    with _encoder_lock:
        if _encoder is None:
            try:
                _encoder = pipeline(
                    "audio-classification",
                    model="asapp/asvspoof2019-laasist",
                    device=0 if torch.cuda.is_available() else -1
                )
                logging.info("AASIST deepfake detector loaded")
            except Exception as e:
                logging.error(f"Failed to load detector: {e}")
                return None
        return _encoder


def analyze_audio(audio_path: str) -> Dict[str, Any]:
    detector = get_deepfake_detector()
    if detector is None:
        return {"is_deepfake": False, "confidence": 0.5, "label": "UNKNOWN", "error": "Detector not available"}
    
    try:
        import soundfile as sf
        import librosa
        audio, sr = librosa.load(audio_path, sr=16000)
        
        results = detector(audio)
        spoof_score = max((r["score"] for r in results if r["label"] == "spoof"), default=0)
        is_fake = spoof_score > 0.7
        
        return {
            "is_deepfake": is_fake,
            "confidence": round(spoof_score, 3),
            "label": "FAKE" if is_fake else "REAL",
            "details": results
        }
    except ImportError as e:
        logging.error(f"Missing dep: {e}")
        return {"is_deepfake": False, "confidence": 0.5, "label": "ERROR", "error": "Audio libs missing"}
    except Exception as e:
        logging.error(f"Analysis failed: {e}")
        return {"is_deepfake": False, "confidence": 0.5, "label": "ERROR", "error": str(e)}


def detect_audio_deepfake(url_or_path: str) -> Dict[str, Any]:
    temp_path = None
    try:
        if url_or_path.startswith("https://"):
            temp_path = safe_audio_download(url_or_path)
            audio_path = temp_path
        else:
            audio_path = safe_file_path(url_or_path)
            if not os.path.isfile(audio_path):
                raise ValueError("File not found")
        return analyze_audio(audio_path)
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
