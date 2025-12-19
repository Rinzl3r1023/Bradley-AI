# Bradley Node Network (Archived - December 2025)

## STATUS: DELAYED UNTIL Q3 2026+

### What This Is

Decentralized peer-to-peer node network for Bradley deepfake detection with:
- Distributed threat broadcasting (P2P relay)
- IPFS publishing (decentralized storage)
- Node reputation system (trust scoring)
- HMAC signature verification (security)
- Rate limiting (spam prevention)
- Encryption (Fernet-based data protection)

### Why Archived

**Decision**: Launch MVP first, then decentralize.

**Timeline**:
- Q4 2025: Built node network prototype
- Q4 2025: Archived (strategic delay)
- Q1 2026: Launch MVP (Chrome extension + centralized API)
- Q2 2026: Validate market demand (crypto nerds, early adopters)
- Q3 2026+: Restore node network (if demand validated)

**Rationale**:
1. MVP faster without P2P complexity (weeks, not months)
2. Centralized API sufficient for validation (simpler)
3. Market validation first (prove demand before decentralizing)
4. Node network adds value AFTER product-market fit (not before)

This follows: Anti-Grid principle (don't build what you don't need yet)

### Architecture Overview

**Components**:
- **ThreadSafeState**: Thread-safe peer/threat management with rate limiting
- **NodeRegistry**: Node registration, discovery, and heartbeat tracking
- **GridNode**: Main node implementation with peer management and threat broadcasting
- **IPFS Integration**: Decentralized storage for threat data
- **Security**: HMAC-SHA256 signatures, endpoint validation, encryption

**Flow**:
1. Node receives threat detection result
2. Validates data schema
3. Signs with HMAC-SHA256
4. Publishes to IPFS (optional encryption)
5. Broadcasts to connected peers
6. Peers validate signature + data
7. Peers relay to their peers (gossip protocol)

### Dependencies
```python
# Core (archived - not needed for MVP)
requests>=2.31.0
cryptography>=41.0.0  # For Fernet encryption

# Environment Variables (for when restored)
GRID_SECRET_KEY=  # Shared secret for HMAC
GRID_ENCRYPTION_KEY=  # Fernet encryption key
IPFS_GATEWAY=https://ipfs.io
IPFS_API_URL=https://ipfs.infura.io:5001
IPFS_PROJECT_ID=
IPFS_PROJECT_SECRET=
```

### Known Issues & TODOs

**When Restoring**:
- [ ] Review and update dependencies (will be outdated)
- [ ] Add comprehensive docstrings
- [ ] Separate async/sync functions (currently mixed)
- [ ] Enhance endpoint validation (DNS rebinding protection)
- [ ] Add unit tests
- [ ] Update integration with current MVP architecture
- [ ] Security audit before production use

### Restoration Checklist

When ready to restore (Q3 2026+):

1. **Review Code**: Check for security updates, update dependencies
2. **Update Architecture**: Integrate with current MVP codebase
3. **Security Audit**: Re-audit all security functions, penetration testing
4. **Testing**: Unit tests, integration tests, load testing
5. **Deployment**: Infrastructure setup, monitoring, gradual rollout

### Design Decisions

**Why IPFS?**: Decentralized storage, content addressing, censorship resistant

**Why HMAC signatures?**: Shared secret model (simpler than PKI), fast verification

**Why rate limiting?**: Spam prevention, network health (10 broadcasts/min per node)

**Why reputation system?**: Trust scoring, identify bad actors, future token incentives

### Key Features

- Max 250 peers per node
- 10 broadcasts per minute rate limit
- 300 second peer timeout
- 1000 threat log entry maximum
- HTTPS-only peer connections
- Public IP validation (no private/loopback)
- Encrypted IPFS publishing (optional)
- Thread-safe operations throughout

---

**Created**: December 2025  
**Archived**: December 19, 2025  
**By**: Chris + Kim (The Business Lounge / Bradley AI)  
**Status**: Awaiting market validation before restoration  
**Next Review**: Q2 2026 (after MVP metrics)
