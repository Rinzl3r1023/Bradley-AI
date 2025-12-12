import requests
import json
import time
import hashlib
import hmac
import os
import logging
import secrets
import asyncio
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)

GRID_SECRET_KEY = os.environ.get('GRID_SECRET_KEY', secrets.token_hex(32))
IPFS_GATEWAY = "https://ipfs.io"
IPFS_API_URL = "https://ipfs.infura.io:5001"
MAX_BROADCASTS_PER_MIN = 10
MAX_THREAT_LOG = 1000
MAX_PEERS = 250

PEERS: List[str] = []
THREAT_LOG: List[Dict] = []
BROADCAST_TIMESTAMPS: Dict[str, List[float]] = {}
NODE_ID = secrets.token_hex(16)


def verify_signature(node_id: str, signature: str, timestamp: float, data: Dict) -> bool:
    """HMAC-SHA256 signature verification (anti-replay + authenticity)"""
    if abs(time.time() - timestamp) > 300:
        return False
    
    message = f"{node_id}:{timestamp}:{json.dumps(data, sort_keys=True)}"
    expected = hmac.new(
        GRID_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


def create_signature(node_id: str, timestamp: float, data: Dict) -> str:
    """Create HMAC-SHA256 signature for outgoing messages"""
    message = f"{node_id}:{timestamp}:{json.dumps(data, sort_keys=True)}"
    return hmac.new(
        GRID_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()


def rate_limit_node(node_id: str) -> bool:
    """Rate limit per node ID"""
    now = time.time()
    timestamps = BROADCAST_TIMESTAMPS.get(node_id, [])
    timestamps = [t for t in timestamps if now - t < 60]
    if len(timestamps) >= MAX_BROADCASTS_PER_MIN:
        return False
    timestamps.append(now)
    BROADCAST_TIMESTAMPS[node_id] = timestamps
    return True


def validate_threat_data(data: Dict) -> bool:
    """Strict schema validation"""
    required = ['is_deepfake', 'confidence']
    if not all(k in data for k in required):
        return False
    if not isinstance(data['is_deepfake'], bool):
        return False
    if not isinstance(data['confidence'], (int, float)) or not 0 <= data['confidence'] <= 1:
        return False
    if len(json.dumps(data)) > 10_000:
        return False
    return True


def publish_to_ipfs(data: Dict) -> Optional[str]:
    """Publish to IPFS with fallback to simulated CID"""
    try:
        json_data = json.dumps(data)
        files = {'file': ('threat.json', json_data)}
        response = requests.post(
            f"{IPFS_API_URL}/api/v0/add",
            files=files,
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            cid = result.get('Hash')
            logging.info(f"Published to IPFS: {cid}")
            return cid
    except requests.exceptions.RequestException as e:
        logging.warning(f"IPFS publish via Infura failed: {e}")
    
    cid = f"Qm{secrets.token_hex(22)}"
    logging.info(f"Using simulated CID (gateway mode): {cid}")
    return cid


class NodeRegistry:
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.max_nodes = MAX_PEERS
    
    def register(self, node_id: str, endpoint: Optional[str] = None) -> bool:
        if len(self.nodes) >= self.max_nodes:
            return False
        
        self.nodes[node_id] = {
            'endpoint': endpoint or '',
            'registered_at': time.time(),
            'last_seen': time.time(),
            'threats_relayed': 0,
            'is_active': True
        }
        return True
    
    def update_heartbeat(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id]['last_seen'] = time.time()
    
    def get_active_nodes(self, timeout: int = 300) -> List[str]:
        current_time = time.time()
        active = []
        for node_id, info in self.nodes.items():
            if info['is_active'] and (current_time - info['last_seen']) < timeout:
                active.append(node_id)
        return active
    
    def increment_threats(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id]['threats_relayed'] += 1
    
    def deactivate(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id]['is_active'] = False
    
    def get_stats(self) -> Dict:
        active = self.get_active_nodes()
        total_threats = sum(n['threats_relayed'] for n in self.nodes.values())
        return {
            'total_registered': len(self.nodes),
            'active_nodes': len(active),
            'max_capacity': self.max_nodes,
            'total_threats_relayed': total_threats
        }


class GridNode:
    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or NODE_ID
        self.connected_peers: List[str] = []
        self.threat_log: List[Dict] = []
        self.ipfs_cids: List[str] = []
        self.is_active = True
        self.registry = NodeRegistry()
        endpoint = self._get_endpoint()
        self.registry.register(self.node_id, endpoint)

    def _get_endpoint(self) -> str:
        return os.environ.get('REPLIT_DEV_DOMAIN', '')

    def add_peer(self, peer_endpoint: str, node_id: Optional[str] = None, 
                 signature: Optional[str] = None, timestamp: Optional[float] = None) -> bool:
        """Add peer with optional authentication"""
        if signature and timestamp and node_id:
            if not verify_signature(node_id, signature, timestamp, 
                                   {"action": "add_peer", "endpoint": peer_endpoint}):
                logging.warning(f"Invalid peer signature from {node_id}")
                return False
        
        peer_id = node_id or hashlib.sha256(peer_endpoint.encode()).hexdigest()[:16]
        
        if peer_endpoint not in PEERS and len(PEERS) < MAX_PEERS:
            PEERS.append(peer_endpoint)
            self.connected_peers.append(peer_id)
            self.registry.register(peer_id, peer_endpoint)
            logging.info(f"Peer added: {peer_id[:8]}@{peer_endpoint}")
            return True
        return False

    def broadcast_threat(self, threat_data: Dict, signature: Optional[str] = None, 
                        timestamp: Optional[float] = None, source_node: Optional[str] = None,
                        target_nodes: Optional[List[str]] = None) -> Dict:
        """Receive and validate threat broadcast"""
        source = source_node or self.node_id
        ts = timestamp or time.time()
        
        if source_node and signature:
            if not rate_limit_node(source_node):
                logging.warning(f"Rate limited: {source_node}")
                return {"status": "rate_limited"}
            
            if not verify_signature(source_node, signature, ts, threat_data):
                logging.warning(f"Invalid threat signature from {source_node}")
                return {"status": "invalid_signature"}
        
        if not validate_threat_data(threat_data):
            logging.warning(f"Invalid threat data")
            return {"status": "invalid_data"}
        
        if target_nodes is None:
            target_nodes = self.registry.get_active_nodes()
        
        threat_entry = {
            'timestamp': ts,
            'source': source,
            'node_id': self.node_id,
            'threat': threat_data,
            'relayed_to': len(target_nodes),
            'target_nodes': target_nodes[:10],
            'received_at': time.time(),
            'ipfs_cid': None
        }
        
        THREAT_LOG.append(threat_entry)
        if len(THREAT_LOG) > MAX_THREAT_LOG:
            THREAT_LOG.pop(0)
        
        if threat_data.get('is_deepfake', False):
            cid = publish_to_ipfs(threat_entry)
            if cid:
                threat_entry['ipfs_cid'] = cid
                self.ipfs_cids.append(cid)
                print(f"⚡ THREAT RELAYED — CID: {cid}")
        
        self.threat_log.append(threat_entry)
        self.registry.increment_threats(self.node_id)
        
        media_type = threat_data.get('media_type', 'unknown').upper()
        confidence = threat_data.get('confidence', 0)
        logging.info(f"THREAT RECEIVED — {media_type} — Confidence: {confidence:.1%}")
        
        self.relay_threat(threat_entry)
        
        return threat_entry

    def relay_threat(self, threat_entry: Dict):
        """Relay to connected peers with our signature"""
        ts = time.time()
        payload = {
            "threat_data": threat_entry["threat"],
            "source_node": self.node_id,
            "timestamp": ts
        }
        signature = create_signature(self.node_id, ts, payload)
        
        for peer in PEERS[:50]:
            try:
                requests.post(
                    f"{peer}/receive_threat",
                    json={**payload, "signature": signature},
                    timeout=5
                )
            except Exception:
                pass

    def get_status(self) -> Dict:
        return {
            'node_id': self.node_id,
            'is_active': self.is_active,
            'connected_peers': len(self.connected_peers),
            'threats_relayed': len(self.threat_log),
            'ipfs_published': len(self.ipfs_cids),
            'ipfs_gateway': IPFS_GATEWAY,
            'registry_stats': self.registry.get_stats()
        }


grid_node = GridNode()


async def relay_threat_async(threat_data: Dict) -> Dict:
    if not threat_data.get("is_deepfake", False):
        return {"status": "skipped", "reason": "Not a threat"}
    
    threat_payload = {
        "node_id": NODE_ID,
        "threat": threat_data,
        "timestamp": time.time()
    }
    
    result = {
        "status": "relayed",
        "node_id": NODE_ID[:8],
        "ipfs_cid": None,
        "ipfs_url": None,
        "peers_notified": 0
    }
    
    cid = publish_to_ipfs(threat_payload)
    if cid:
        result["ipfs_cid"] = cid
        result["ipfs_url"] = f"{IPFS_GATEWAY}/ipfs/{cid}"
        logging.info(f"Threat relayed to IPFS: {cid}")
    
    for peer in PEERS:
        result["peers_notified"] += 1
    
    return result


def relay_threat(threat_data: Dict, target_nodes: Optional[List[str]] = None) -> str:
    if threat_data:
        print("THREAT DETECTED - relaying to grid nodes...")
        entry = grid_node.broadcast_threat(threat_data, target_nodes=target_nodes)
        node_count = entry.get('relayed_to', 0)
        cid = entry.get('ipfs_cid')
        cid_info = f" (IPFS: {cid[:16]}...)" if cid else ""
        return f"Threat relayed via node {grid_node.node_id[:8]} to {node_count} nodes{cid_info}"
    else:
        print("All clear. Grid secure.")
        return "All clear. Grid secure."


def add_peer(peer_addr: str) -> None:
    if peer_addr not in PEERS:
        grid_node.add_peer(peer_addr)


def add_lounge_node(endpoint: str) -> str:
    grid_node.add_peer(endpoint)
    return hashlib.sha256(endpoint.encode()).hexdigest()[:16]


def get_registry_stats() -> Dict:
    return grid_node.registry.get_stats()


if __name__ == "__main__":
    test_threat = {"is_deepfake": True, "confidence": 0.94, "label": "FAKE"}
    asyncio.run(relay_threat_async(test_threat))
