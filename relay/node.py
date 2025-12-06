import os
import time
import hashlib
import json
from typing import Dict, List, Optional


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
        self.node_id = node_id or self._generate_node_id()
        self.connected_peers: List[str] = []
        self.threat_log: List[Dict] = []
        self.is_active = True
        self.registry = NodeRegistry()
        self.registry.register(self.node_id, self._get_endpoint())
    
    def _generate_node_id(self) -> str:
        timestamp = str(time.time()).encode()
        return hashlib.sha256(timestamp).hexdigest()[:16]
    
    def _get_endpoint(self) -> Optional[str]:
        return os.environ.get('REPLIT_DEV_DOMAIN')
    
    def add_peer(self, peer_endpoint: str) -> str:
        peer_id = hashlib.sha256(peer_endpoint.encode()).hexdigest()[:16]
        if peer_id not in self.connected_peers:
            self.connected_peers.append(peer_id)
            self.registry.register(peer_id, peer_endpoint)
        return peer_id
    
    def broadcast_threat(self, threat_data: Dict, target_nodes: List[str] = None) -> Dict:
        if target_nodes is None:
            target_nodes = self.registry.get_active_nodes()
        
        threat_entry = {
            'timestamp': time.time(),
            'node_id': self.node_id,
            'threat': threat_data,
            'relayed_to': len(target_nodes),
            'target_nodes': target_nodes[:10]
        }
        self.threat_log.append(threat_entry)
        self.registry.increment_threats(self.node_id)
        
        return threat_entry
    
    def get_status(self) -> Dict:
        return {
            'node_id': self.node_id,
            'is_active': self.is_active,
            'connected_peers': len(self.connected_peers),
            'threats_relayed': len(self.threat_log),
            'registry_stats': self.registry.get_stats()
        }


grid_node = GridNode()


def relay_threat(threat_data: Dict, target_nodes: List[str] = None) -> str:
    if threat_data:
        print("THREAT DETECTED - relaying to grid nodes...")
        entry = grid_node.broadcast_threat(threat_data, target_nodes)
        node_count = entry['relayed_to']
        return f"Threat relayed via node {grid_node.node_id[:8]} to {node_count} nodes..."
    else:
        print("All clear. Grid secure.")
        return "All clear. Grid secure."


def add_lounge_node(endpoint: str) -> str:
    return grid_node.add_peer(endpoint)


def get_registry_stats() -> Dict:
    return grid_node.registry.get_stats()
