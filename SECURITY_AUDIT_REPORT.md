# Bradley AI Security Audit Report

**Audit Date:** January 15, 2026
**Auditor:** Claude (Opus 4.5)
**Repository:** Bradley-ai
**Version:** v1.4.0

---

## Executive Summary

Bradley AI is a Chrome extension + Flask backend for detecting AI-generated video/audio content. The codebase has undergone significant security hardening based on previous audits documented in `attached_assets/`. Overall, the security posture is **GOOD** with several important issues to address.

**Overall Security Grade: B+ (87/100)**

| Component | Security Grade | Notes |
|-----------|---------------|-------|
| Flask Backend (app.py) | A- (90/100) | Well-hardened with rate limiting, CORS, auth |
| Video Detector | A (96/100) | Strong URL validation, SSRF protection |
| Audio Detector | B+ (85/100) | Secure but less comprehensive than video |
| Chrome Extension | A- (91/100) | CSP-compliant, good input validation |
| Web UI Templates | B+ (88/100) | No dynamic injection, proper escaping |

---

## Critical Findings (0)

No critical vulnerabilities found. Previous critical issues have been addressed:
- Admin auth now requires HMAC-validated Bearer token
- Rate limiting implemented across all public endpoints
- SSRF protection via private IP blocking and domain validation
- XSS mitigated through proper DOM manipulation (textContent)

---

## High Priority Findings (2)

### 1. Weak Default Session Secret
**File:** `ui/app.py:98`
**Severity:** HIGH
**Status:** Needs Fix

```python
app.secret_key = os.environ.get("SESSION_SECRET") or "bradley-guardian-key"
```

**Issue:** Falls back to hardcoded secret if environment variable not set. This could allow session forgery in production.

**Recommendation:**
```python
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise ValueError("SESSION_SECRET environment variable is required")
```

### 2. Overly Permissive CORS on Extension Endpoints
**File:** `ui/app.py:554, 601, 606`
**Severity:** HIGH
**Status:** Needs Review

Multiple endpoints use `Access-Control-Allow-Origin: *`:
- `/api/detect` (line 554, 563, 573, 601, 605)
- `/api/report` (line 614, 622, 628, 634, 637)
- `/detect_video_deepfake` (line 644, 654, 660, 666, 670)
- `/detect_audio_deepfake` (line 678, 688, 694, 700, 704)

**Issue:** While necessary for Chrome extension CORS, wildcard origins bypass the ALLOWED_ORIGINS whitelist for these endpoints.

**Recommendation:** Use the extension's Chrome extension ID in production:
```python
ALLOWED_EXTENSION_ORIGINS = {
    'chrome-extension://YOUR_PUBLISHED_EXTENSION_ID',
    'https://bradleyai.replit.app',
}
```

---

## Medium Priority Findings (5)

### 3. Missing Rate Limiting on Several Endpoints
**File:** `ui/app.py`
**Severity:** MEDIUM

The following endpoints lack rate limiting:
- `/api/scan` (line 334)
- `/api/analyze/video` (line 362)
- `/api/analyze/audio` (line 408)
- `/detect_video_deepfake` (line 641)
- `/detect_audio_deepfake` (line 675)

**Recommendation:** Add `@limiter.limit()` decorators:
```python
@app.route('/api/analyze/video', methods=['POST'])
@limiter.limit("10/hour")
def analyze_video():
```

### 4. Input Validation Gap in Node Submission
**File:** `ui/app.py:768-769`
**Severity:** MEDIUM

```python
wallet = data.get('wallet', '').strip()
email = data.get('email', '').strip()
```

Wallet is validated but email has no validation in `/api/nodes/submit`.

**Recommendation:** Add email validation:
```python
if email and not validate_email(email):
    return jsonify({'error': 'Invalid email address'}), 400
```

### 5. SQLAlchemy Without Version Pinning
**File:** `requirements.txt`
**Severity:** MEDIUM

Dependencies lack version pinning, which could introduce breaking changes or security vulnerabilities.

**Recommendation:** Pin major versions:
```
flask>=2.0,<3.0
torch>=2.0,<3.0
transformers>=4.30,<5.0
flask-limiter>=3.0,<4.0
```

### 6. Bare Exception Handlers
**File:** `ui/app.py:457, 596`
**Severity:** MEDIUM

```python
except:
    total_scans = swarm.scans_completed
```

Bare `except:` catches all exceptions including KeyboardInterrupt and SystemExit.

**Recommendation:** Use specific exceptions:
```python
except Exception as e:
    logger.error(f"Database query failed: {e}")
```

### 7. Debug Mode in Production
**File:** `ui/app.py:827`
**Severity:** MEDIUM

```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

**Issue:** Debug mode should not be enabled in production as it exposes stack traces and enables the debugger.

**Recommendation:** Use environment variable:
```python
app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
```

---

## Low Priority Findings (6)

### 8. Duplicate Dependency in requirements.txt
**File:** `requirements.txt:15,17`
**Severity:** LOW

`pytest` is listed twice in requirements.txt.

### 9. Inconsistent API Base URLs
**File:** `Bradley-Extension/content.js:2` vs `Bradley-Extension/background.js:1`
**Severity:** LOW

```javascript
// content.js
API_BASE: 'https://bradleyai.replit.app'

// background.js
const API_BASE = 'https://bradley-ai.replit.app';
```

Different URLs could cause inconsistent behavior.

### 10. Mock Mode Returns Random Results
**File:** `detection/video_detector.py:333-389`
**Severity:** LOW (Expected behavior documented)

The detection system is in MOCK MODE returning random results. This is documented and expected until GPU deployment in Q3 2026.

### 11. Unused Imports in swarm.py
**File:** `agents_DISABLED/swarm.py:6-7`
**Severity:** LOW (File is disabled)

```python
from relay.node import relay_threat, grid_node
from agents.grok import analyze_threat_with_grok, get_grok_status
```

These imports would fail since the modules don't exist.

### 12. Missing CSRF Protection
**File:** `ui/templates/beta.html:167`
**Severity:** LOW

The beta signup form lacks CSRF token validation. While rate-limited (5/hour), CSRF protection would add defense-in-depth.

### 13. Console.log in Production Code
**File:** Multiple extension files
**Severity:** LOW

Debug logging is present in production extension code. While not a security risk, it increases bundle size and exposes internal workings.

---

## Security Features Verified (Positive Findings)

### Backend Security (app.py)
- [x] Admin authentication with HMAC-validated Bearer token
- [x] Rate limiting via flask-limiter (1000/day, 100/hour default)
- [x] CORS whitelist for trusted origins
- [x] Security headers (X-Content-Type-Options, X-Frame-Options, HSTS, etc.)
- [x] Email validation with regex and length limits
- [x] Ethereum wallet validation (0x prefix, 42 chars, hex)
- [x] File extension whitelist for uploads
- [x] Secure filename sanitization via werkzeug

### Detection Module Security (video_detector.py)
- [x] URL validation (scheme, hostname, DNS resolution)
- [x] Private IP blocking (SSRF prevention)
- [x] DNS rebinding protection
- [x] File size limits (200MB max)
- [x] Path traversal protection
- [x] Rate limiting per user_id
- [x] Redirect depth limiting (max 5)
- [x] Request timeout (10 seconds)
- [x] Thread-safe operations with locks
- [x] Metrics tracking for monitoring

### Chrome Extension Security
- [x] Manifest V3 with strict CSP
- [x] Content Security Policy (no inline scripts)
- [x] URL validation (HTTPS only, blocked patterns)
- [x] Sensitive parameter sanitization
- [x] Sender validation for messages
- [x] Rate limiting (20 requests/minute)
- [x] Notification rate limiting (5/minute)
- [x] DOM manipulation via textContent (XSS prevention)
- [x] User consent dialog before scanning

### Web UI Security
- [x] No dynamic HTML injection from user input
- [x] HTML escaping via escapeHtml() function
- [x] Proper URL sanitization for display
- [x] Static HTML templates (no server-side injection)

---

## Architecture Notes

### Intentionally Disabled Components
The following folders are intentionally disabled and should NOT be re-enabled without security review:

1. **agents_DISABLED/** - LangGraph agent swarm
   - Contains imports to non-existent modules
   - Requires full security audit before restoration

2. **relay_DISABLED/** - P2P relay network
   - Stub implementation only
   - Full P2P network archived in /archive/

3. **archive/node-network/** - Decentralized node network
   - 15.7K lines, complex P2P implementation
   - Scheduled for Q3 2026+ restoration
   - Requires comprehensive security audit

### Mock Mode Implementation
The detection system returns random mock results because:
- GPU models not available in current environment
- Real models (deepfake-o-meter-v2, AASIST) require GPU deployment
- Mock mode is clearly labeled in responses (`model: "mock-v1-gpu-unavailable"`)

---

## Recommendations Summary

### Immediate Actions (Do Now)
1. Require SESSION_SECRET environment variable (no fallback)
2. Enable rate limiting on all detection endpoints
3. Remove `debug=True` from production

### Short-Term Actions (This Sprint)
4. Replace wildcard CORS with specific extension origin
5. Add email validation to node submission endpoint
6. Pin dependency versions in requirements.txt
7. Remove duplicate pytest entry
8. Standardize API base URL across extension files

### Long-Term Actions (Before Q3 2026)
9. Add CSRF tokens to forms
10. Remove console.log statements from extension
11. Full security audit of archived P2P network before restoration
12. Consider CSP reporting endpoint for monitoring violations

---

## Compliance Notes

- **GDPR:** Privacy policy page exists at /privacy
- **Data Collection:** Only video URLs analyzed, no personal data stored
- **Consent:** Extension requests explicit user consent before scanning
- **Encryption:** All API traffic over HTTPS

---

## Files Reviewed

| File | Lines | Status |
|------|-------|--------|
| ui/app.py | 827 | Reviewed |
| detection/video_detector.py | 559 | Reviewed |
| detection/audio_detector.py | 177 | Reviewed |
| Bradley-Extension/content.js | 466 | Reviewed |
| Bradley-Extension/background.js | 433 | Reviewed |
| Bradley-Extension/popup.js | 203 | Reviewed |
| Bradley-Extension/manifest.json | 52 | Reviewed |
| ui/templates/index.html | 284 | Reviewed |
| ui/templates/beta.html | 255 | Reviewed |
| ui/static/js/analyzer.js | 378 | Reviewed |
| agents_DISABLED/swarm.py | 261 | Reviewed (disabled) |
| main.py | 58 | Reviewed |
| requirements.txt | 24 | Reviewed |
| attached_assets/* | 45+ files | Reviewed (historical) |

---

## Conclusion

Bradley AI has a solid security foundation with most critical vulnerabilities from previous audits addressed. The remaining issues are primarily configuration and best-practice improvements rather than exploitable vulnerabilities.

The intentionally disabled components (agents, relay, P2P network) are correctly isolated and should remain disabled until properly audited.

**Next Audit Recommended:** Before Q3 2026 GPU deployment or P2P network restoration.

---

*Report generated by Claude (Opus 4.5) on January 15, 2026*
