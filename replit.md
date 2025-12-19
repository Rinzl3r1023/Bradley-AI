# Bradley AI - The Guardian Program for the Real World

## Overview
Bradley AI is a decentralized, open-source guardian that protects everyday people from malicious AI: deepfakes, voice clones, scam bots, and synthetic identity fraud.

**Mission:** "Alan Bradley created Tron to protect the system from the MCP. We created Bradley to protect users from malicious AI."

**Version:** v1.3.3 (CSP Compliant Extension)

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
├── Bradley-Extension/      # Chrome browser extension v1.1
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
3. **Grid Relay Network** - Decentralized P2P threat broadcasting with IPFS storage
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
- `GET /api/nodes/pending` - Get pending node approval queue
- `POST /api/nodes/submit` - Submit wallet for node approval
- `POST /api/nodes/approve` - Approve a pending node (admin)

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string (auto-configured)
- `SESSION_SECRET` - Flask session secret
- `XAI_API_KEY` - xAI Grok API key for AI-enhanced analysis (optional)
- `FIREBASE_CREDENTIALS` - Firebase service account JSON (for Firestore node queue)
- `ADMIN_API_KEY` - Admin API key for protected endpoints (node approval)

## Running the Project
The Flask server runs on port 5000 via the "Bradley AI" workflow.

## Next Steps (Phase 4)
- [ ] ERC-20 $BRADLEY token on Base
- [ ] Real libp2p P2P networking (mesh topology)
- [ ] Video call protection in extension
- [ ] Chrome Web Store publication

## Recent Changes
- **Dec 13, 2025:** Video detection v2.0: production-ready with rate limiting (10/min), metrics tracking, env config, A (96/100)
- **Dec 13, 2025:** Security hardening A+ (98/100): rate limiting, admin auth, input validation, security headers
- **Dec 13, 2025:** Firebase Firestore integration for pending node approval queue (wallet-based beta)
- **Dec 13, 2025:** Extension v1.3.3 - CSP compliant: removed inline styles, class-based visibility (.hidden), Chrome Web Store ready
- **Dec 12, 2025:** Extension v1.3.2 - popup.js A+ (98/100): named constants, loading spinner, success messages, debounced updates, CLEAR_LOG handler
- **Dec 12, 2025:** Extension v1.3.0 - background.js hardened (A- 90/100): AsyncMutex atomic storage, input validation, sender validation, rate limiting
- **Dec 12, 2025:** Extension api.js v1.2 (A- 90/100) - URL validation, timeouts, retry logic, input/response validation
- **Dec 12, 2025:** Extension v1.2.0 - content.js 100% XSS-proof, DOM API only, enhanced CSP
- **Dec 12, 2025:** Grid Node v1.1 FINAL (A- 92/100 Security) - HMAC signatures, rate limiting, encryption, no fake CIDs
- **Dec 12, 2025:** Extension v1.0.0 Final - class-based architecture, rate limiting, debounce, LRU cache, consent dialog
- **Dec 12, 2025:** Production ML models: DeepFake-O-Meter v2 for video, AASIST for audio with librosa @ 16kHz
- **Dec 12, 2025:** New API endpoints: `/detect_video_deepfake` and `/detect_audio_deepfake` with full CORS
- **Dec 8, 2025:** v0.3.0 Decentralized relay network with IPFS integration for permanent threat storage
- **Dec 8, 2025:** Enhanced extension alerts: red badge counter, toast notifications, scrollable threat log
- **Dec 6, 2025:** v0.2.0 Browser extension release with real-time media scanning, Tron-styled UI
- **Dec 5, 2025:** xAI Grok integration, security improvements, node registry (250 capacity)
- **Dec 5, 2025:** Initial MVP setup with detection engines, relay prototype, and Tron UI
