from typing import Dict, TypedDict
from langgraph.graph import StateGraph, END

from detection.video_detector import detect_video_deepfake
from detection.audio_detector import detect_audio_deepfake
from relay.node import relay_threat, grid_node
from agents.grok import analyze_threat_with_grok, get_grok_status


class ThreatState(TypedDict):
    video_path: str
    audio_path: str
    video_result: Dict
    audio_result: Dict
    relay_status: str
    threat_level: str
    grok_analysis: Dict
    scan_complete: bool


def video_analysis_agent(state: ThreatState) -> ThreatState:
    print("[VIDEO AGENT] Analyzing video for deepfakes...")
    result = detect_video_deepfake(state["video_path"])
    return {"video_result": result}


def audio_analysis_agent(state: ThreatState) -> ThreatState:
    print("[AUDIO AGENT] Analyzing audio for voice clones...")
    result = detect_audio_deepfake(state["audio_path"])
    return {"audio_result": result}


def threat_assessment_agent(state: ThreatState) -> ThreatState:
    print("[THREAT AGENT] Assessing combined threat level...")
    
    video_threat = state.get("video_result", {}).get("is_deepfake", False)
    audio_threat = state.get("audio_result", {}).get("is_deepfake", False)
    video_conf = state.get("video_result", {}).get("confidence", 0)
    audio_conf = state.get("audio_result", {}).get("confidence", 0)
    
    if video_threat and audio_threat:
        threat_level = "CRITICAL"
    elif video_threat or audio_threat:
        max_conf = max(video_conf, audio_conf)
        if max_conf > 0.9:
            threat_level = "HIGH"
        elif max_conf > 0.7:
            threat_level = "MEDIUM"
        else:
            threat_level = "LOW"
    else:
        threat_level = "CLEAR"
    
    return {"threat_level": threat_level}


def relay_agent(state: ThreatState) -> ThreatState:
    print("[RELAY AGENT] Broadcasting to grid nodes...")
    
    threat_level = state.get("threat_level", "CLEAR")
    
    if threat_level != "CLEAR":
        threat_data = {
            "video": state.get("video_result"),
            "audio": state.get("audio_result"),
            "level": threat_level
        }
        status = relay_threat(threat_data)
    else:
        status = "All clear. Grid secure."
    
    return {"relay_status": status, "scan_complete": True}


def should_relay(state: ThreatState) -> str:
    threat_level = state.get("threat_level", "CLEAR")
    if threat_level in ["CRITICAL", "HIGH", "MEDIUM"]:
        return "relay"
    return "end"


def create_bradley_graph():
    workflow = StateGraph(ThreatState)
    
    workflow.add_node("video_analysis", video_analysis_agent)
    workflow.add_node("audio_analysis", audio_analysis_agent)
    workflow.add_node("threat_assessment", threat_assessment_agent)
    workflow.add_node("relay", relay_agent)
    
    workflow.set_entry_point("video_analysis")
    workflow.add_edge("video_analysis", "audio_analysis")
    workflow.add_edge("audio_analysis", "threat_assessment")
    workflow.add_conditional_edges(
        "threat_assessment",
        should_relay,
        {
            "relay": "relay",
            "end": END
        }
    )
    workflow.add_edge("relay", END)
    
    return workflow.compile()


class BradleySwarm:
    def __init__(self):
        self.threats_detected = 0
        self.scans_completed = 0
        self.graph = None
        self._init_graph()
    
    def _init_graph(self):
        try:
            self.graph = create_bradley_graph()
            print("[SWARM] LangGraph agent swarm initialized")
        except Exception as e:
            print(f"[SWARM] Graph initialization failed: {e}, using fallback")
            self.graph = None
    
    def run_sample_threat(self):
        print("Scanning sample threat...")
        
        initial_state = {
            "video_path": "sample.mp4",
            "audio_path": "sample.wav",
            "video_result": {},
            "audio_result": {},
            "relay_status": "",
            "threat_level": "CLEAR",
            "scan_complete": False
        }
        
        if self.graph:
            try:
                result = self.graph.invoke(initial_state)
                video_result = result.get("video_result", {})
                audio_result = result.get("audio_result", {})
                relay_status = result.get("relay_status", "")
                threat_level = result.get("threat_level", "CLEAR")
            except Exception as e:
                print(f"[SWARM] Graph execution failed: {e}, using fallback")
                video_result, audio_result, relay_status, threat_level = self._fallback_scan()
        else:
            video_result, audio_result, relay_status, threat_level = self._fallback_scan()
        
        self.scans_completed += 1
        if video_result.get('is_deepfake') or audio_result.get('is_deepfake'):
            self.threats_detected += 1
        
        grok_analysis = None
        grok_status = get_grok_status()
        if grok_status.get('configured'):
            print("[GROK AGENT] Performing AI-enhanced threat analysis...")
            grok_analysis = analyze_threat_with_grok({
                'video_result': video_result,
                'audio_result': audio_result,
                'threat_level': threat_level
            })
        
        print(f"\nThreat Level: {threat_level}")
        print("Bradley AI standing by.")
        
        return {
            'video_result': video_result,
            'audio_result': audio_result,
            'relay_status': relay_status,
            'threat_level': threat_level,
            'grok_analysis': grok_analysis,
            'grok_enabled': grok_status.get('configured', False),
            'scans_completed': self.scans_completed,
            'threats_detected': self.threats_detected
        }
    
    def _fallback_scan(self):
        video_result = detect_video_deepfake("sample.mp4")
        audio_result = detect_audio_deepfake("sample.wav")
        
        is_threat = video_result.get('is_deepfake') or audio_result.get('is_deepfake')
        relay_status = relay_threat(video_result if is_threat else None)
        
        if video_result.get('is_deepfake') and audio_result.get('is_deepfake'):
            threat_level = "CRITICAL"
        elif is_threat:
            threat_level = "HIGH"
        else:
            threat_level = "CLEAR"
        
        return video_result, audio_result, relay_status, threat_level
    
    def get_status(self):
        grok_status = get_grok_status()
        return {
            'scans_completed': self.scans_completed,
            'threats_detected': self.threats_detected,
            'status': 'online',
            'graph_enabled': self.graph is not None,
            'grok_enabled': grok_status.get('configured', False)
        }
