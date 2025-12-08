from transformers import pipeline
import cv2
import numpy as np
from PIL import Image, ImageFile
import io
import requests
import urllib.parse
import socket
import ipaddress
import logging
import os

logging.basicConfig(level=logging.INFO)

ALLOWED_DOMAINS = ['huggingface.co', 'cdn.huggingface.co']
ALLOWED_SCHEMES = ['https']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_IMAGE_PIXELS = 10000 * 10000  # 100MP limit
ImageFile.LOAD_TRUNCATED_IMAGES = False
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

def is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.strip('[]'))
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_reserved or
            ip.is_multicast or
            ip.is_unspecified or
            ipaddress.ip_network('100.64.0.0/10').overlaps(ipaddress.ip_network(f'{ip}/32'))
        )
    except ValueError:
        return False

def safe_request(url: str):
    parsed = urllib.parse.urlparse(url)
    try:
        ip = socket.gethostbyname(parsed.hostname)
        if is_private_ip(ip):
            raise ValueError("Resolves to private IP")
    except socket.gaierror:
        raise ValueError("Invalid hostname")
    
    response = requests.get(url, timeout=(5, 15), stream=True, allow_redirects=False)
    if response.is_redirect:
        redirect_url = response.headers.get('Location')
        if redirect_url:
            safe_request(redirect_url)
    
    content = bytearray()
    for chunk in response.iter_content(chunk_size=8192):
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise ValueError("File exceeded size limit during download")
    
    return content

def detect_video_deepfake(url_or_path):
    try:
        if url_or_path.startswith("http"):
            content = safe_request(url_or_path)
            img = Image.open(io.BytesIO(content))
        else:
            real_path = os.path.realpath(url_or_path)
            if not real_path.startswith(os.path.realpath(os.getcwd() + os.sep)):
                raise ValueError("Path outside allowed directory")
            if not os.path.isfile(real_path):
                raise ValueError("File not found")
            img = Image.open(real_path)
        
        if img.width * img.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image dimensions too large")
        
        img = img.convert('RGB')
        
        detector = pipeline("image-classification", model="umm-maybe/AI-image-detector")
        result = detector(img)
        
        fake_score = 0.0
        for item in result:
            label = item['label'].lower()
            if 'artificial' in label or 'fake' in label or 'ai' in label:
                fake_score = item['score']
                break
            elif 'human' in label or 'real' in label:
                fake_score = 1 - item['score']
                break
        
        score = fake_score
        is_fake = score > 0.7
        
        return {
            "is_deepfake": is_fake,
            "confidence": round(score, 3),
            "label": "FAKE" if is_fake else "REAL"
        }
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        return {"error": str(e), "is_deepfake": False, "confidence": 0.0}
    except Exception as e:
        logging.critical(f"Unexpected error: {e}")
        return {"error": "Processing failed", "is_deepfake": False, "confidence": 0.0}
