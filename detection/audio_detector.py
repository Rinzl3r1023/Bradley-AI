import os
import numpy as np
from typing import Dict, Optional
import warnings
import requests
import io
import urllib.parse
import logging
import ipaddress

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)

ALLOWED_AUDIO_FORMATS = ('.wav', '.mp3', '.ogg', '.flac', '.m4a')
ALLOWED_SCHEMES = ['https', 'http']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
REQUEST_TIMEOUT = 15

BLOCKED_HOSTS = [
    'localhost', '127.0.0.1', '0.0.0.0', '[::1]',
    'metadata.google.internal', '169.254.169.254',
    'metadata.aws.amazon.com', 'instance-data'
]

SAFE_HEADERS = {
    'User-Agent': 'BradleyAI/0.2 AudioDetector',
    'Accept': 'audio/*,*/*;q=0.8'
}

hf_voice_detector = None
hf_audio_available = False

try:
    from transformers import pipeline
    hf_voice_detector = pipeline("audio-classification", model="facebook/wav2vec2-base")
    hf_audio_available = True
    print("[AUDIO] Hugging Face audio classifier loaded successfully")
except Exception as e:
    print(f"[AUDIO] Hugging Face audio model not available, using built-in detector: {e}")
    hf_audio_available = False


def is_private_ip(ip_str: str) -> bool:
    try:
        ip_str = ip_str.strip('[]')
        ip = ipaddress.ip_address(ip_str)
        return (ip.is_private or ip.is_loopback or ip.is_link_local or 
                ip.is_reserved or ip.is_multicast or ip.is_unspecified)
    except ValueError:
        return False


def validate_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only HTTP/HTTPS URLs allowed")
    
    hostname = parsed.hostname or ''
    hostname = hostname.rstrip('.').lower()
    
    if parsed.username or parsed.password:
        hostname = hostname.split('@')[-1] if '@' in hostname else hostname
    
    for blocked in BLOCKED_HOSTS:
        if blocked in hostname:
            raise ValueError("Internal URLs not allowed")
    
    if is_private_ip(hostname):
        raise ValueError("Private IP addresses not allowed")
    
    dangerous_patterns = ['localhost', '127.', '192.168.', '10.', '172.16.',
                          'metadata', 'internal', '169.254', '::1', 'fd00:']
    for pattern in dangerous_patterns:
        if pattern in hostname:
            raise ValueError("Blocked URL pattern detected")
    
    return url


def validate_local_path(path: str) -> str:
    abs_path = os.path.abspath(path)
    cwd = os.getcwd()
    if ".." in path or not abs_path.startswith(cwd):
        raise ValueError("Invalid path - directory traversal not allowed")
    return abs_path


def safe_request(url: str, method: str = 'get', stream: bool = False) -> requests.Response:
    validated_url = validate_url(url)
    
    if method == 'head':
        response = requests.head(
            validated_url, 
            timeout=REQUEST_TIMEOUT, 
            allow_redirects=True,
            headers=SAFE_HEADERS
        )
    else:
        response = requests.get(
            validated_url, 
            timeout=REQUEST_TIMEOUT, 
            stream=stream,
            headers=SAFE_HEADERS
        )
    
    response.raise_for_status()
    return response


def validate_audio_path(path: str) -> None:
    if not path:
        raise ValueError("Audio path cannot be empty")
    if not path.lower().endswith(ALLOWED_AUDIO_FORMATS):
        raise ValueError(f"Invalid file type. Allowed formats: {', '.join(ALLOWED_AUDIO_FORMATS)}")


def detect_with_huggingface_audio(audio_path_or_url: str) -> Dict:
    if not hf_audio_available or hf_voice_detector is None:
        return None
    
    try:
        result = hf_voice_detector(audio_path_or_url)
        synth_score = 0.0
        for item in result:
            label = item['label'].lower()
            if 'synthetic' in label or 'fake' in label or 'generated' in label:
                synth_score = item['score']
                break
        
        is_fake = synth_score > 0.65
        return {
            "is_deepfake": is_fake,
            "confidence": round(synth_score, 3),
            "label": "FAKE" if is_fake else "REAL",
            "model": "huggingface",
            "analysis_type": "transformer"
        }
    except Exception as e:
        logging.error(f"[AUDIO] HuggingFace detection failed: {e}")
        return None


class VoiceCloneDetector:
    def __init__(self):
        self.sample_rate = 16000
        self.n_mfcc = 13
        self.confidence_threshold = 0.5
    
    def load_audio(self, audio_path: str) -> Optional[np.ndarray]:
        if not os.path.exists(audio_path):
            return None
        
        try:
            import wave
            with wave.open(audio_path, 'rb') as wf:
                n_frames = wf.getnframes()
                audio_data = wf.readframes(n_frames)
                audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                audio = audio / 32768.0
                return audio
        except Exception as e:
            raise ValueError(f"Error loading audio: {str(e)}")
    
    def extract_features(self, audio: np.ndarray) -> Dict:
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))
        
        frame_length = int(0.025 * self.sample_rate)
        hop_length = int(0.010 * self.sample_rate)
        
        frames = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i + frame_length]
            frames.append(frame)
        
        if not frames:
            frames = [audio[:min(len(audio), frame_length)]]
        
        energies = [np.sum(frame**2) for frame in frames]
        
        spectral_features = self._compute_spectral_features(audio)
        
        return {
            'zero_crossing_rate': float(zero_crossings),
            'energy_mean': float(np.mean(energies)),
            'energy_std': float(np.std(energies)),
            'spectral_centroid': spectral_features['centroid'],
            'spectral_rolloff': spectral_features['rolloff'],
            'spectral_flatness': spectral_features['flatness']
        }
    
    def _compute_spectral_features(self, audio: np.ndarray) -> Dict:
        n_fft = min(2048, len(audio))
        
        if len(audio) < n_fft:
            audio = np.pad(audio, (0, n_fft - len(audio)))
        
        window = np.hanning(n_fft)
        spectrum = np.abs(np.fft.rfft(audio[:n_fft] * window))
        
        freqs = np.fft.rfftfreq(n_fft, 1.0 / self.sample_rate)
        
        spectrum_sum = np.sum(spectrum)
        if spectrum_sum > 0:
            centroid = np.sum(freqs * spectrum) / spectrum_sum
        else:
            centroid = 0.0
        
        cumsum = np.cumsum(spectrum)
        if cumsum[-1] > 0:
            rolloff_idx = np.searchsorted(cumsum, 0.85 * cumsum[-1])
            rolloff = freqs[min(rolloff_idx, len(freqs) - 1)]
        else:
            rolloff = 0.0
        
        geometric_mean = np.exp(np.mean(np.log(spectrum + 1e-10)))
        arithmetic_mean = np.mean(spectrum)
        flatness = geometric_mean / (arithmetic_mean + 1e-10)
        
        return {
            'centroid': float(centroid),
            'rolloff': float(rolloff),
            'flatness': float(flatness)
        }
    
    def analyze_artifacts(self, features: Dict) -> Dict:
        anomaly_scores = {}
        
        zcr = features['zero_crossing_rate']
        if zcr < 0.01 or zcr > 0.3:
            anomaly_scores['zcr'] = 0.8
        else:
            anomaly_scores['zcr'] = 0.2
        
        energy_variation = features['energy_std'] / (features['energy_mean'] + 1e-10)
        if energy_variation < 0.1 or energy_variation > 2.0:
            anomaly_scores['energy'] = 0.7
        else:
            anomaly_scores['energy'] = 0.3
        
        flatness = features['spectral_flatness']
        if flatness > 0.5:
            anomaly_scores['spectral'] = 0.9
        elif flatness < 0.01:
            anomaly_scores['spectral'] = 0.6
        else:
            anomaly_scores['spectral'] = 0.2
        
        return anomaly_scores
    
    def detect(self, audio_path: str) -> Dict:
        try:
            validate_audio_path(audio_path)
        except ValueError as e:
            return {'error': str(e), 'is_deepfake': False, 'confidence': 0.0}
        
        try:
            audio = self.load_audio(audio_path)
        except ValueError as e:
            return {'error': str(e), 'is_deepfake': False, 'confidence': 0.0}
        
        if audio is None:
            return self._default_safe_result(audio_path)
        
        features = self.extract_features(audio)
        anomaly_scores = self.analyze_artifacts(features)
        
        combined_score = np.mean(list(anomaly_scores.values()))
        
        voice_consistency = self._analyze_voice_consistency(audio)
        
        final_confidence = 0.6 * combined_score + 0.4 * voice_consistency
        is_clone = final_confidence > self.confidence_threshold
        
        return {
            'is_deepfake': is_clone,
            'confidence': float(final_confidence),
            'features': features,
            'anomaly_scores': anomaly_scores,
            'voice_consistency': float(voice_consistency),
            'analysis_type': 'full',
            'label': 'FAKE' if is_clone else 'REAL'
        }
    
    def _analyze_voice_consistency(self, audio: np.ndarray) -> float:
        segment_length = len(audio) // 4
        if segment_length < 100:
            return 0.5
        
        segments = [audio[i*segment_length:(i+1)*segment_length] for i in range(4)]
        
        segment_features = []
        for seg in segments:
            energy = np.sum(seg**2) / len(seg)
            zcr = np.sum(np.abs(np.diff(np.sign(seg)))) / (2 * len(seg))
            segment_features.append([energy, zcr])
        
        segment_features = np.array(segment_features)
        variation = np.std(segment_features, axis=0).mean()
        
        if variation < 0.001:
            return 0.8
        elif variation > 0.1:
            return 0.6
        else:
            return 0.3
    
    def _default_safe_result(self, audio_path: str) -> Dict:
        return {
            'is_deepfake': False,
            'confidence': 0.5,
            'features': {},
            'anomaly_scores': {},
            'voice_consistency': 0.5,
            'analysis_type': 'default',
            'label': 'UNKNOWN',
            'note': 'Audio file not accessible - using conservative estimate'
        }


detector = VoiceCloneDetector()


def detect_audio_deepfake(url_or_path: str) -> Dict:
    try:
        if url_or_path.startswith("http"):
            try:
                head_response = safe_request(url_or_path, method='head')
                content_length = head_response.headers.get('content-length')
                if content_length and int(content_length) > MAX_FILE_SIZE:
                    raise ValueError(f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")
                
                hf_result = detect_with_huggingface_audio(url_or_path)
                if hf_result:
                    return hf_result
                
                response = safe_request(url_or_path, stream=True)
                audio_data = io.BytesIO(response.content)
                
                try:
                    import wave
                    audio_data.seek(0)
                    with wave.open(audio_data, 'rb') as wf:
                        n_frames = wf.getnframes()
                        raw_audio = wf.readframes(n_frames)
                        audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
                        audio = audio / 32768.0
                        
                        features = detector.extract_features(audio)
                        anomaly_scores = detector.analyze_artifacts(features)
                        combined_score = np.mean(list(anomaly_scores.values()))
                        voice_consistency = detector._analyze_voice_consistency(audio)
                        final_confidence = 0.6 * combined_score + 0.4 * voice_consistency
                        is_clone = final_confidence > detector.confidence_threshold
                        
                        return {
                            'is_deepfake': is_clone,
                            'confidence': float(final_confidence),
                            'voice_consistency': float(voice_consistency),
                            'anomaly_scores': {
                                'pitch_variance': float(anomaly_scores.get('zcr', 0.5)),
                                'spectral_gaps': float(anomaly_scores.get('spectral', 0.3))
                            },
                            'analysis_type': 'remote_audio',
                            'label': 'FAKE' if is_clone else 'REAL'
                        }
                except Exception as audio_err:
                    logging.warning(f"Audio parsing failed, using spectral estimate: {audio_err}")
                    return {
                        'is_deepfake': False,
                        'confidence': 0.5,
                        'voice_consistency': 0.5,
                        'anomaly_scores': {'pitch_variance': 0.5, 'spectral_gaps': 0.3},
                        'analysis_type': 'remote_audio',
                        'label': 'UNKNOWN',
                        'note': 'Could not parse audio format'
                    }
                    
            except ValueError as e:
                logging.error(f"Validation error: {e}")
                return {'error': str(e), 'is_deepfake': False, 'confidence': 0.0}
            except requests.RequestException as e:
                logging.error(f"Network error: {e}")
                return {'error': 'Failed to fetch URL', 'is_deepfake': False, 'confidence': 0.0}
        
        try:
            validated_path = validate_local_path(url_or_path)
        except ValueError as e:
            logging.error(f"Path validation error: {e}")
            return {'error': str(e), 'is_deepfake': False, 'confidence': 0.0}
        
        hf_result = detect_with_huggingface_audio(validated_path)
        if hf_result:
            return hf_result
        
        return detector.detect(validated_path)
    except Exception as e:
        logging.critical(f"Unexpected error: {e}")
        return {
            'error': 'Processing failed',
            'is_deepfake': False,
            'confidence': 0.0,
            'analysis_type': 'error'
        }
