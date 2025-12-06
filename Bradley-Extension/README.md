# Bradley AI Browser Extension v0.2.0

Real-time deepfake and voice-clone detection while you browse. Powered by the Bradley Grid.

## Installation (Chrome/Brave/Edge)

1. Download this `Bradley-Extension` folder
2. Open your browser and go to `chrome://extensions/` (or `edge://extensions/` for Edge)
3. Enable "Developer mode" (toggle in top-right corner)
4. Click "Load unpacked" 
5. Select the `Bradley-Extension` folder
6. The Bradley AI icon should appear in your browser toolbar

## Features

- **Real-time Media Scanning**: Automatically detects and analyzes video/audio elements on web pages
- **Threat Notifications**: Get instant alerts when potential deepfakes are detected
- **Visual Indicators**: See scan status directly on media elements
- **Privacy-Focused**: Only analyzes public media URLs, no personal data collected
- **Grid Integration**: Connected to the Bradley AI threat intelligence network

## How It Works

1. When you visit any webpage, Bradley scans for `<video>` and `<audio>` elements
2. Each media element is analyzed via the Bradley AI detection API
3. Results are displayed as an overlay on the media element:
   - Green checkmark = Verified safe
   - Red warning = Potential deepfake detected
4. High-confidence threats trigger a full-screen warning overlay

## API Endpoints Used

- `POST /api/detect` - Analyze media URL for deepfake indicators
- `GET /api/status` - Check Bradley AI server status
- `POST /api/report` - Report false positives/negatives

## Configuration

The extension connects to the Bradley AI backend at:
`https://bradley-ai.replit.app`

To use with a local development server, modify the `BRADLEY_API` constant in:
- `content.js`
- `popup.js`
- `background.js`

## Permissions Required

- `activeTab` - Access current page content
- `storage` - Save settings and threat counts
- `notifications` - Show threat alerts
- `<all_urls>` - Scan media on any website

## Privacy

- Only public media URLs are sent to the API
- No browsing history or personal data is collected
- All communication uses HTTPS
- Scan results are stored locally in your browser

## Troubleshooting

**Extension not detecting media:**
- Ensure the extension is enabled in your browser
- Check that the Bradley AI server is online (visit dashboard)
- Some video players use blob/data URLs which cannot be analyzed

**Warning overlay not showing:**
- Verify notifications permission is granted
- Check if popups are blocked for the site

## Version History

- **v0.2.0** - Initial release with real-time scanning, Tron UI, and Grid integration
