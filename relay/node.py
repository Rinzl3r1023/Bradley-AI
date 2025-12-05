import time
import hashlib
import json

class GridNode:
    def __init__(self, node_id=None):
        self.node_id = node_id or self._generate_node_id()
        self.connected_peers = []
        self.threat_log = []
        self.is_active = True
    
    def _generate_node_id(self):
        timestamp = str(time.time()).encode()
        return hashlib.sha256(timestamp).hexdigest()[:16]
    
    def broadcast_threat(self, threat_data):
        threat_entry = {
            'timestamp': time.time(),
            'node_id': self.node_id,
            'threat': threat_data,
            'relayed_to': len(self.connected_peers)
        }
        self.threat_log.append(threat_entry)
        return threat_entry
    
    def get_status(self):
        return {
            'node_id': self.node_id,
            'is_active': self.is_active,
            'connected_peers': len(self.connected_peers),
            'threats_relayed': len(self.threat_log)
        }

grid_node = GridNode()

def relay_threat(threat_data):
    if threat_data:
        print("THREAT DETECTED - relaying to grid nodes...")
        entry = grid_node.broadcast_threat(threat_data)
        return f"Threat relayed via node {grid_node.node_id[:8]}..."
    else:
        print("All clear. Grid secure.")
        return "All clear. Grid secure."
