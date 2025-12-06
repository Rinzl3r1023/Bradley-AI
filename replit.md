# Bradley AI - The Guardian Program for the Real World

## Overview
Bradley AI is a decentralized, open-source guardian that protects everyday people from malicious AI: deepfakes, voice clones, scam bots, and synthetic identity fraud.

**Mission:** "Alan Bradley created Tron to protect the system from the MCP. We created Bradley to protect users from malicious AI."

**Version:** v0.2.0 (Browser Extension Release)

## Project Structure
```
Bradley-AI/
├── main.py                 # CLI entry point
├── agents/
│   ├── swarm.py           # Bradley agent swarm coordinator
│   └── grok.py            # xAI Grok integration for AI analysis
├── detection/
│   ├── video_detector.py  # Deepfake video detection (PyTorch CNN)
│   └── audio_detector.py  # Voice clone detection (spectral analysis)
├── relay/
│   └── node.py            # Grid relay node for threat broadcasting
├── ui/
│   ├── app.py             # Flask web application
│   ├── templates/
│   │   ├── index.html     # Main dashboard
│   │   └── beta.html      # Closed beta signup
│   └── static/
│       ├── css/style.css  # Tron neon-grid styling
│       └── js/main.js     # Frontend interaction
├── Bradley-Extension/      # Chrome browser extension v0.2
│   ├── manifest.json      # Extension manifest (MV3)
│   ├── background.js      # Service worker
│   ├── content.js         # Media scanner
│   ├── popup.html/js/css  # Extension popup UI
│   └── icons/             # Tron-styled icons
└── uploads/               # Temporary file uploads
```

## Tech Stack
- **Backend:** Python 3.11, Flask, SQLAlchemy
- **ML/Detection:** PyTorch (CPU), OpenCV, NumPy
- **Database:** PostgreSQL (Replit managed)
- **Frontend:** HTML/CSS/JS with Tron-inspired neon-grid UI

## Key Features (MVP)
1. **Deepfake Video Detection** - CNN-based analysis with artifact detection
2. **Voice Clone Detection** - Spectral analysis and consistency checking
3. **Grid Relay Network** - Simulated P2P threat broadcasting
4. **Threat Logging** - PostgreSQL database for detection history
5. **Closed Beta Signup** - Onboarding for Business Lounge members
6. **Tron UI** - Cyberpunk neon-grid interface

## API Endpoints
- `GET /` - Main dashboard
- `GET /beta` - Beta signup page
- `POST /api/scan` - Run demo threat scan
- `POST /api/analyze/video` - Upload and analyze video
- `POST /api/analyze/audio` - Upload and analyze audio
- `GET /api/status` - System status
- `GET /api/detections` - Recent detection history
- `POST /api/beta/signup` - Register for beta
- `GET /api/node/status` - Grid node status with registry stats
- `GET /api/registry/stats` - Node registry statistics (capacity: 250)
- `POST /api/registry/add` - Add Business Lounge node to registry
- `POST /api/detect` - Extension API: Analyze remote media URL (CORS enabled)
- `POST /api/report` - Extension API: Report threat for community review

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string (auto-configured)
- `SESSION_SECRET` - Flask session secret
- `XAI_API_KEY` - xAI Grok API key for AI-enhanced analysis (optional)

## Running the Project
The Flask server runs on port 5000 via the "Bradley AI" workflow.

## Next Steps (Phase 3)
- [ ] ERC-20 $BRADLEY token on Base
- [ ] Real libp2p P2P networking
- [ ] IPFS integration for evidence storage
- [ ] Video call protection in extension
- [ ] Chrome Web Store publication

## Recent Changes
- **Dec 6, 2025:** Real ML deepfake detection with Hugging Face transformers (umm-maybe/AI-image-detector for video, facebook/wav2vec2-base for audio)
- **Dec 6, 2025:** v0.2.0 Browser extension release with real-time media scanning, Tron-styled UI, and backend /detect API
- **Dec 5, 2025:** xAI Grok integration, security improvements, node registry (250 capacity)
- **Dec 5, 2025:** Initial MVP setup with detection engines, relay prototype, and Tron UI
