import requests
import urllib.parse
import socket
import ipaddress
import logging
import os
import tempfile
from threading import Lock
from typing import Dict, Any, Optional
import torch
from transformers import pipeline

logging.basicConfig(level=logging.INFO)

ALLOWED_DOMAINS = ["huggingface.co", "cdn.huggingface.co"]
ALLOWED_SCHEMES = ["https"]
MAX_REDIRECTS = 5
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB video

_detector = None
_detector_lock = Lock()


def is_allowed_domain(hostname: str) -> bool:
    hostname = hostname.lower()
    return any(hostname == d or hostname.endswith("." + d) for d in ALLOWED_DOMAINS)


def is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return (
            addr.is_private or addr.is_loopback or addr.is_link_local or
            addr.is_multicast or addr.is_reserved or
            (addr.version == 4 and 100 << 24 <= int(addr) <= 103 << 24)
        )
    except ValueError:
        return True


def validate_url(url: str) -> Optional[str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
        return None
    if not is_allowed_domain(parsed.hostname):
        return None
    try:
        for addr in socket.getaddrinfo(parsed.hostname, None):
            if is_private_ip(addr[4][0]):
                return None
    except Exception:
        return None
    return url


def safe_request(url: str, depth: int = 0) -> requests.Response:
    if depth > MAX_REDIRECTS:
        raise ValueError("Too many redirects")
    if not validate_url(url):
        raise ValueError(f"Disallowed URL: {url}")
    resp = requests.get(url, allow_redirects=False, timeout=20, stream=True)
    if resp.is_redirect:
        location = resp.headers.get("Location")
        if location:
            next_url = urllib.parse.urljoin(url, location)
            return safe_request(next_url, depth + 1)
    resp.raise_for_status()
    return resp


def safe_file_path(path: str) -> str:
    base_dir = os.path.realpath(os.getcwd())
    real_path = os.path.realpath(path)
    if not real_path.startswith(base_dir + os.sep):
        raise ValueError(f"Path traversal attempt: {path}")
    return real_path


def safe_video_download(url: str) -> str:
    resp = safe_request(url)
    total = 0
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            for chunk in resp.iter_content(8192):
                total += len(chunk)
                if total > MAX_FILE_SIZE:
                    raise ValueError("File too large")
                f.write(chunk)
        return path
    except Exception:
        if os.path.exists(path):
            os.unlink(path)
        raise


def get_video_detector():
    global _detector
    with _detector_lock:
        if _detector is None:
            _detector = pipeline(
                "video-classification",
                model="datarootsio/deepfake-o-meter-v2",
                device=0 if torch.cuda.is_available() else -1
            )
            logging.info("DeepFake-O-Meter v2 loaded")
        return _detector


def analyze_video(video_path: str) -> Dict[str, Any]:
    detector = get_video_detector()
    try:
        results = detector(video_path)
        fake_score = max((r["score"] for r in results if r["label"] == "FAKE"), default=0)
        is_fake = fake_score > 0.75
        return {
            "is_deepfake": is_fake,
            "confidence": round(fake_score, 3),
            "label": "FAKE" if is_fake else "REAL",
            "details": results
        }
    except Exception as e:
        logging.error(f"Video analysis failed: {e}")
        return {"is_deepfake": False, "confidence": 0.0, "error": str(e)}


def detect_video_deepfake(url_or_path: str) -> Dict[str, Any]:
    temp_path = None
    try:
        if url_or_path.startswith("https://"):
            temp_path = safe_video_download(url_or_path)
            video_path = temp_path
        else:
            video_path = safe_file_path(url_or_path)
            if not os.path.isfile(video_path):
                raise ValueError("File not found")
        return analyze_video(video_path)
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
