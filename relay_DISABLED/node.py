"""
Bradley AI Relay Node - STUB (Node Network Archived)

The full P2P node network is archived in archive/node-network/
This stub provides the API interface without P2P functionality.

Status: Archived until Q3 2026+
See: archive/node-network/README.md for restoration plan
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NODE_REGISTRY_CAPACITY = 250


class GridNodeStub:
    """Minimal stub for GridNode - no P2P functionality."""
    
    def __init__(self):
        self.node_id = str(uuid.uuid4())
        self.registered_nodes: Dict[str, Dict[str, Any]] = {}
        logger.info(f"[GRID STUB] Node initialized (P2P disabled): {self.node_id[:8]}")
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id[:8],
            'status': 'stub',
            'message': 'P2P node network archived - using centralized API',
            'peers': 0,
            'threats_logged': 0,
            'uptime': 0,
            'registry': {
                'registered': len(self.registered_nodes),
                'capacity': NODE_REGISTRY_CAPACITY,
                'available': NODE_REGISTRY_CAPACITY - len(self.registered_nodes)
            }
        }


grid_node = GridNodeStub()


def get_registry_stats() -> Dict[str, Any]:
    """Get node registry statistics."""
    return {
        'registered': len(grid_node.registered_nodes),
        'capacity': NODE_REGISTRY_CAPACITY,
        'available': NODE_REGISTRY_CAPACITY - len(grid_node.registered_nodes),
        'status': 'stub',
        'message': 'Node network archived - see archive/node-network/'
    }


def add_lounge_node(endpoint: str) -> Optional[str]:
    """Add a Business Lounge node (stub - just registers the endpoint)."""
    if len(grid_node.registered_nodes) >= NODE_REGISTRY_CAPACITY:
        return None
    
    node_id = str(uuid.uuid4())
    grid_node.registered_nodes[node_id] = {
        'endpoint': endpoint,
        'registered_at': datetime.utcnow().isoformat(),
        'status': 'pending_activation'
    }
    logger.info(f"[GRID STUB] Node registered: {node_id[:8]} -> {endpoint}")
    return node_id


def relay_threat(threat_data: Optional[Dict[str, Any]], target_nodes: Optional[list] = None) -> str:
    """Relay threat to network (stub - logs only, no P2P broadcast)."""
    if threat_data is None:
        return "no_threat"
    logger.info(f"[GRID STUB] Threat logged (P2P disabled): {str(threat_data)[:100]}...")
    return "logged_locally"
