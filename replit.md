# Bradley AI - The Guardian Program for the Real World

## Overview
Bradley AI is a decentralized, open-source guardian that protects everyday people from malicious AI: deepfakes, voice clones, scam bots, and synthetic identity fraud.

**Mission:** "Alan Bradley created Tron to protect the system from the MCP. We created Bradley to protect users from malicious AI."

**Version:** v0.1.0 (MVP)

## Project Structure
```
Bradley-AI/
├── main.py                 # CLI entry point
├── agents/
│   └── swarm.py           # Bradley agent swarm coordinator
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

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string (auto-configured)
- `SESSION_SECRET` - Flask session secret

## Running the Project
The Flask server runs on port 5000 via the "Bradley AI" workflow.

## Next Steps (Phase 2)
- [ ] ERC-20 $BRADLEY token on Base
- [ ] Real libp2p P2P networking
- [ ] IPFS integration for evidence storage
- [ ] LangGraph agent orchestration
- [ ] Browser extension for video call protection

## Recent Changes
- **Dec 5, 2025:** Initial MVP setup with detection engines, relay prototype, and Tron UI
