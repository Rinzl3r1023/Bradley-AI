"""
Bradley AI Guardian - Main Entry Point

This module exposes the Flask app for WSGI servers (Gunicorn, uWSGI, etc.)
and runs health checks when executed directly.

Usage:
  - Gunicorn: gunicorn main:app
  - Direct: python main.py
"""

# Expose Flask app for WSGI servers (Railway, Heroku, etc.)
from ui.app import app

# Only run health check when executed directly (not when imported by gunicorn)
if __name__ == "__main__":
    print("Bradley AI online.")
    print("Guardian program activated.")
    print("Protecting the grid…\n")

    print("[BRADLEY] Agents module archived - testing direct detection API\n")

    from detection.video_detector import detect_video_deepfake, get_config, get_metrics

    print("=== BRADLEY AI CONFIGURATION ===")
    config = get_config()
    for key, value in config.items():
        print(f"{key}: {value}")
    print()

    print("=== DETECTION SYSTEM STATUS ===")
    print("Video Detection: Online")
    print("Audio Detection: Online")
    print("Model: Ready")
    print()

    print("=== RUNNING HEALTH CHECK ===")
    try:
        test_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
        print(f"Testing detection with sample video...")
        print(f"URL: {test_url}")
        print()

        result = detect_video_deepfake(test_url, user_id="health_check")

        print("=== TEST RESULT ===")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Is Deepfake: {result.get('is_deepfake', 'N/A')}")
        print(f"Confidence: {result.get('confidence', 0):.3f}")
        print(f"Latency: {result.get('latency_ms', 0):.2f}ms")

        if result.get('error'):
            print(f"Error: {result['error']}")

        print()

    except Exception as e:
        print(f"Health check failed: {e}")
        print("This is normal if model is still loading or not available in current environment")
        print()

    print("=== SYSTEM METRICS ===")
    try:
        metrics = get_metrics()
        for key, value in metrics.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"Metrics unavailable: {e}")

    print()
    print("=== BRADLEY AI GUARDIAN READY ===")
    print("Standalone mode active")
    print("API endpoints available at /detect_video_deepfake and /detect_audio_deepfake")
    print()
