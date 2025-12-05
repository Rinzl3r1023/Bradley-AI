from detection.video_detector import detect_video_deepfake
from detection.audio_detector import detect_audio_deepfake
from relay.node import relay_threat

class BradleySwarm:
    def __init__(self):
        self.threats_detected = 0
        self.scans_completed = 0
    
    def run_sample_threat(self):
        print("Scanning sample threat...")
        video_result = detect_video_deepfake("sample.mp4")
        audio_result = detect_audio_deepfake("sample.wav")
        
        print(f"Video threat: {video_result}")
        print(f"Audio threat: {audio_result}")
        
        relay_status = relay_threat(video_result or audio_result)
        
        self.scans_completed += 1
        if video_result.get('is_deepfake') or audio_result.get('is_deepfake'):
            self.threats_detected += 1
        
        print("\nBradley AI standing by.")
        
        return {
            'video_result': video_result,
            'audio_result': audio_result,
            'relay_status': relay_status,
            'scans_completed': self.scans_completed,
            'threats_detected': self.threats_detected
        }
    
    def get_status(self):
        return {
            'scans_completed': self.scans_completed,
            'threats_detected': self.threats_detected,
            'status': 'online'
        }
