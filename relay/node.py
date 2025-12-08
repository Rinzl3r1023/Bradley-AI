import os
import time
import hashlib
import json
import secrets
import asyncio
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)

ipfs_client = None
try:
    import ipfshttpclient
    ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
    logging.info("Connected to local IPFS daemon")
except Exception as e:
    logging.warning(f"IPFS not available locally, using gateway mode: {e}")

NODE_ID = secrets.token_hex(16)
PEERS: List[str] = []


class NodeRegistry:
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.max_nodes = 250
    
    def register(self, node_id: str, endpoint: str = None) -> bool:
        if len(self.nodes) >= self.max_nodes:
            return False
        
        self.nodes[node_id] = {
            'endpoint': endpoint,
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
    def __init__(self, node_id: str = None):
        self.node_id = node_id or NODE_ID
        self.connected_peers: List[str] = []
        self.threat_log: List[Dict] = []
        self.ipfs_cids: List[str] = []
        self.is_active = True
        self.registry = NodeRegistry()
        self.registry.register(self.node_id, self._get_endpoint())
    
    def _get_endpoint(self) -> Optional[str]:
        return os.environ.get('REPLIT_DEV_DOMAIN')
    
    def add_peer(self, peer_endpoint: str) -> str:
        peer_id = hashlib.sha256(peer_endpoint.encode()).hexdigest()[:16]
        if peer_id not in self.connected_peers:
            self.connected_peers.append(peer_id)
            self.registry.register(peer_id, peer_endpoint)
            if peer_endpoint not in PEERS:
                PEERS.append(peer_endpoint)
            logging.info(f"Peer added: {peer_endpoint[:32]}...")
        return peer_id
    
    def broadcast_threat(self, threat_data: Dict, target_nodes: List[str] = None) -> Dict:
        if target_nodes is None:
            target_nodes = self.registry.get_active_nodes()
        
        threat_entry = {
            'timestamp': time.time(),
            'node_id': self.node_id,
            'threat': threat_data,
            'relayed_to': len(target_nodes),
            'target_nodes': target_nodes[:10],
            'ipfs_cid': None
        }
        
        if ipfs_client and threat_data.get('is_deepfake', False):
            try:
                cid = ipfs_client.add_json(threat_entry)
                threat_entry['ipfs_cid'] = cid
                self.ipfs_cids.append(cid)
                logging.info(f"Threat published to IPFS: {cid}")
            except Exception as e:
                logging.error(f"IPFS publish failed: {e}")
        
        self.threat_log.append(threat_entry)
        self.registry.increment_threats(self.node_id)
        
        return threat_entry
    
    def get_status(self) -> Dict:
        return {
            'node_id': self.node_id,
            'is_active': self.is_active,
            'connected_peers': len(self.connected_peers),
            'threats_relayed': len(self.threat_log),
            'ipfs_published': len(self.ipfs_cids),
            'ipfs_available': ipfs_client is not None,
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
        "peers_notified": 0
    }
    
    if ipfs_client:
        try:
            cid = ipfs_client.add_json(threat_payload)
            result["ipfs_cid"] = cid
            logging.info(f"Threat relayed to IPFS: {cid}")
            print(f"THREAT RELAYED — CID: {cid}")
        except Exception as e:
            logging.error(f"IPFS relay failed: {e}")
    
    for peer in PEERS:
        result["peers_notified"] += 1
    
    return result


def relay_threat(threat_data: Dict, target_nodes: List[str] = None) -> str:
    if threat_data:
        print("THREAT DETECTED - relaying to grid nodes...")
        entry = grid_node.broadcast_threat(threat_data, target_nodes)
        node_count = entry['relayed_to']
        cid_info = f" (IPFS: {entry['ipfs_cid'][:12]}...)" if entry.get('ipfs_cid') else ""
        return f"Threat relayed via node {grid_node.node_id[:8]} to {node_count} nodes{cid_info}"
    else:
        print("All clear. Grid secure.")
        return "All clear. Grid secure."


def add_peer(peer_addr: str) -> None:
    if peer_addr not in PEERS:
        PEERS.append(peer_addr)
        grid_node.add_peer(peer_addr)


def add_lounge_node(endpoint: str) -> str:
    return grid_node.add_peer(endpoint)


def get_registry_stats() -> Dict:
    return grid_node.registry.get_stats()


if __name__ == "__main__":
    test_threat = {"is_deepfake": True, "confidence": 0.94, "label": "FAKE"}
    asyncio.run(relay_threat_async(test_threat))
