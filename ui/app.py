import os
import sys
import json
import hmac
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.orm import DeclarativeBase
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, firestore

firestore_db = None

def init_firebase():
    global firestore_db
    if firebase_admin._apps:
        firestore_db = firestore.client()
        return True
    
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    if not firebase_creds:
        print("[BRADLEY] FIREBASE_CREDENTIALS not set - Firestore disabled")
        return False
    
    try:
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        firestore_db = firestore.client()
        print("[BRADLEY] Firebase Firestore initialized successfully")
        return True
    except json.JSONDecodeError:
        print("[BRADLEY] Invalid Firebase JSON format")
        return False
    except Exception as e:
        print(f"[BRADLEY] Firebase init failed: {e}")
        return False


ALLOWED_ORIGINS = {
    'https://bradleyai.replit.app',
    'https://bradley-ai.replit.app',
}


def require_admin_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        token = auth[7:]
        expected = os.environ.get('ADMIN_API_KEY')
        if not expected or not hmac.compare_digest(token, expected):
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated


def validate_email(email):
    if not email or not isinstance(email, str):
        return False
    email = email.strip().lower()
    if len(email) > 255:
        return False
    import re
    pattern = re.compile(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$')
    return bool(pattern.match(email))


def validate_wallet(wallet):
    if not wallet or not isinstance(wallet, str):
        return False
    wallet = wallet.strip()
    if not wallet.startswith('0x'):
        return False
    if len(wallet) != 42:
        return False
    try:
        int(wallet[2:], 16)
        return True
    except ValueError:
        return False

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "bradley-guardian-key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri="memory://",
)

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac', 'm4a'}

import ipaddress
import socket
import re

BLOCKED_HOSTS = [
    'localhost', 'localhost.', 'localhost.localdomain',
    'metadata.google.internal', 'metadata.google.internal.',
    'metadata.internal', 'metadata.internal.',
    '169.254.169.254', 'metadata', 'kubernetes.default'
]

IPV6_LITERAL_PATTERN = re.compile(r'^\[([^\]]+)\]')

def is_private_ip(ip_str):
    try:
        ip_str = ip_str.strip('[]')
        ip = ipaddress.ip_address(ip_str)
        
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_reserved or
            ip.is_multicast or
            (hasattr(ip, 'is_global') and not ip.is_global and not ip.is_unspecified)
        )
    except ValueError:
        return False

def validate_media_url(url):
    if not url:
        return False, "URL is required"
    
    if len(url) > 2048:
        return False, "URL too long"
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        if parsed.scheme not in ('http', 'https'):
            return False, "Only http/https URLs allowed"
        
        if not parsed.netloc:
            return False, "Invalid URL format"
        
        host = parsed.netloc.lower()
        
        if '@' in host:
            host = host.split('@')[-1]
        
        ipv6_match = IPV6_LITERAL_PATTERN.match(host)
        if ipv6_match:
            ipv6_addr = ipv6_match.group(1)
            if is_private_ip(ipv6_addr):
                return False, "Private IP addresses not allowed"
            host = host[ipv6_match.end():]
            if host.startswith(':'):
                host = host[1:]
            if not host:
                return True, None
        
        if ':' in host:
            host = host.split(':')[0]
        
        host = host.rstrip('.')
        
        if host in BLOCKED_HOSTS or f"{host}." in BLOCKED_HOSTS:
            return False, "Internal URLs not allowed"
        
        if is_private_ip(host):
            return False, "Private IP addresses not allowed"
        
        dangerous_patterns = [
            'localhost', 'internal', 'metadata', 'kubernetes',
            '127.', '10.', '192.168.', '172.16.', '172.17.', '172.18.',
            '172.19.', '172.20.', '172.21.', '172.22.', '172.23.',
            '172.24.', '172.25.', '172.26.', '172.27.', '172.28.',
            '172.29.', '172.30.', '172.31.', '169.254.', '0.0.0.0',
            'fd00:', 'fc00:', 'fe80:', '::1', '::ffff:'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in host:
                return False, "Potentially unsafe URL"
        
        return True, None
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"

db.init_app(app)

from detection.video_detector import detect_video_deepfake
from detection.audio_detector import detect_audio_deepfake

class GridNodeStub:
    node_id = "standalone-node-001"
    def get_status(self):
        return {"status": "standalone", "node_id": self.node_id}

grid_node = GridNodeStub()

def get_registry_stats():
    return {"total_nodes": 1, "active_nodes": 1}

def add_lounge_node(endpoint):
    return "stub-node-id"

class SwarmStub:
    """Stub for disabled BradleySwarm - agents module archived for MVP"""
    scans_completed = 0
    threats_detected = 0
    def run_sample_threat(self):
        return {
            "status": "demo", 
            "message": "Swarm disabled for MVP",
            "video_result": {"is_deepfake": False, "confidence": 0.0},
            "audio_result": {"is_deepfake": False, "confidence": 0.0}
        }
    def analyze_remote_media(self, url, media_type):
        return {
            "status": "disabled", 
            "message": "Use /detect_video_deepfake or /detect_audio_deepfake endpoints", 
            "is_deepfake": False, 
            "confidence": 0.0
        }

swarm = SwarmStub()

class ThreatDetection(db.Model):
    __tablename__ = 'threat_detections'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    detection_type = db.Column(db.String(20), nullable=False)
    file_name = db.Column(db.String(255), nullable=True)
    is_threat = db.Column(db.Boolean, default=False)
    confidence = db.Column(db.Float, nullable=False)
    model_score = db.Column(db.Float, nullable=True)
    artifact_score = db.Column(db.Float, nullable=True)
    analysis_type = db.Column(db.String(50), nullable=True)
    relay_status = db.Column(db.String(255), nullable=True)
    node_id = db.Column(db.String(64), nullable=True)
    raw_result = db.Column(db.JSON, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'detection_type': self.detection_type,
            'file_name': self.file_name,
            'is_threat': self.is_threat,
            'confidence': self.confidence,
            'model_score': self.model_score,
            'artifact_score': self.artifact_score,
            'analysis_type': self.analysis_type,
            'relay_status': self.relay_status,
            'node_id': self.node_id
        }


class BetaUser(db.Model):
    __tablename__ = 'beta_users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    referral_source = db.Column(db.String(100), nullable=True)
    wallet_address = db.Column(db.String(100), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'joined_at': self.joined_at.isoformat(),
            'is_approved': self.is_approved,
            'referral_source': self.referral_source
        }


with app.app_context():
    db.create_all()

def allowed_file(filename, file_type):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if file_type == 'video':
        return ext in ALLOWED_VIDEO_EXTENSIONS
    elif file_type == 'audio':
        return ext in ALLOWED_AUDIO_EXTENSIONS
    return False


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/beta')
def beta_signup():
    return render_template('beta.html')


@app.route('/api/scan', methods=['POST'])
def scan():
    try:
        result = swarm.run_sample_threat()
        
        try:
            detection = ThreatDetection(
                detection_type='sample',
                is_threat=result['video_result'].get('is_deepfake', False) or result['audio_result'].get('is_deepfake', False),
                confidence=max(result['video_result'].get('confidence', 0), result['audio_result'].get('confidence', 0)),
                model_score=result['video_result'].get('model_score'),
                artifact_score=result['video_result'].get('artifact_score'),
                analysis_type='sample_scan',
                relay_status=result.get('relay_status'),
                node_id=grid_node.node_id,
                raw_result=result
            )
            db.session.add(detection)
            db.session.commit()
        except Exception as e:
            print(f"Database error: {e}")
            db.session.rollback()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Scan failed: {str(e)}'}), 500


@app.route('/api/analyze/video', methods=['POST'])
def analyze_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename, 'video'):
        return jsonify({'error': 'Invalid file type. Allowed: mp4, avi, mov, mkv, webm'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(filepath)
    
    try:
        result = detect_video_deepfake(filepath)
        
        detection = ThreatDetection(
            detection_type='video',
            file_name=filename,
            is_threat=result.get('is_deepfake', False),
            confidence=result.get('confidence', 0),
            model_score=result.get('model_score'),
            artifact_score=result.get('artifact_score'),
            analysis_type=result.get('analysis_type'),
            node_id=grid_node.node_id,
            raw_result=result
        )
        db.session.add(detection)
        db.session.commit()
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify(result)
    
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/audio', methods=['POST'])
def analyze_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename, 'audio'):
        return jsonify({'error': 'Invalid file type. Allowed: wav, mp3, ogg, flac, m4a'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(filepath)
    
    try:
        result = detect_audio_deepfake(filepath)
        
        detection = ThreatDetection(
            detection_type='audio',
            file_name=filename,
            is_threat=result.get('is_deepfake', False),
            confidence=result.get('confidence', 0),
            analysis_type=result.get('analysis_type'),
            node_id=grid_node.node_id,
            raw_result=result
        )
        db.session.add(detection)
        db.session.commit()
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify(result)
    
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def status():
    try:
        total_scans = db.session.query(ThreatDetection).count()
        threats_detected = db.session.query(ThreatDetection).filter_by(is_threat=True).count()
    except:
        total_scans = swarm.scans_completed
        threats_detected = swarm.threats_detected
    
    return jsonify({
        'status': 'online',
        'guardian': 'Bradley AI',
        'version': 'v0.2.0',
        'nodes_active': 1,
        'threats_detected': threats_detected,
        'total_scans': total_scans,
        'node_id': grid_node.node_id[:8]
    })


@app.route('/api/detections')
def get_detections():
    try:
        detections = db.session.query(ThreatDetection).order_by(ThreatDetection.created_at.desc()).limit(50).all()
        return jsonify([d.to_dict() for d in detections])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/beta/signup', methods=['POST'])
@limiter.limit("5/hour")
def beta_signup_submit():
    data = request.get_json(silent=True) or {}
    
    email = data.get('email', '').strip().lower()
    wallet = data.get('wallet_address', '').strip()
    
    if not validate_email(email):
        return jsonify({'error': 'Invalid email address'}), 400
    
    if wallet and not validate_wallet(wallet):
        return jsonify({'error': 'Invalid wallet address'}), 400
    
    try:
        existing = db.session.query(BetaUser).filter_by(email=email).first()
        if existing:
            return jsonify({'error': 'Email already registered'}), 409
        
        user = BetaUser(
            email=email,
            name=data.get('name'),
            referral_source=data.get('referral_source', 'business_lounge'),
            wallet_address=wallet if wallet else None
        )
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Welcome to the Bradley AI closed beta!',
            'user': user.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/node/status')
def node_status():
    return jsonify(grid_node.get_status())


@app.route('/api/registry/stats')
def registry_stats():
    try:
        stats = get_registry_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/registry/add', methods=['POST'])
def add_node():
    try:
        data = request.get_json()
        if not data or not data.get('endpoint'):
            return jsonify({'error': 'Node endpoint is required'}), 400
        
        node_id = add_lounge_node(data['endpoint'])
        return jsonify({
            'success': True,
            'node_id': node_id,
            'message': f'Node {node_id[:8]} added to registry'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect', methods=['POST', 'OPTIONS'])
def detect_media():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Bradley-Extension')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        if not data:
            response = jsonify({'error': 'No data provided', 'is_deepfake': False, 'confidence': 0})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        media_url = data.get('url')
        media_type = data.get('type', 'video')
        page_url = data.get('page_url', '')
        
        is_valid, error_msg = validate_media_url(media_url)
        if not is_valid:
            response = jsonify({'error': error_msg, 'is_deepfake': False, 'confidence': 0})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        if media_type not in ('video', 'audio'):
            media_type = 'video'
        
        result = swarm.analyze_remote_media(media_url, media_type)
        
        try:
            detection = ThreatDetection(
                detection_type=f'extension_{media_type}',
                file_name=media_url[:255],
                is_threat=result.get('is_deepfake', False),
                confidence=result.get('confidence', 0),
                model_score=result.get('model_score'),
                artifact_score=result.get('artifact_score'),
                analysis_type='extension_scan',
                relay_status=result.get('relay_status'),
                node_id=grid_node.node_id,
                raw_result={**result, 'page_url': page_url}
            )
            db.session.add(detection)
            db.session.commit()
        except Exception as db_err:
            print(f"Database error: {db_err}")
            db.session.rollback()
        
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    
    except Exception as e:
        response = jsonify({'error': str(e), 'is_deepfake': False, 'confidence': 0})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@app.route('/api/report', methods=['POST', 'OPTIONS'])
def report_threat():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Bradley-Extension')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        if not data:
            response = jsonify({'error': 'No data provided'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        print(f"[REPORT] Threat reported: {data}")
        
        response = jsonify({
            'success': True,
            'message': 'Threat reported successfully',
            'report_id': grid_node.node_id[:8] + '-' + str(int(datetime.utcnow().timestamp()))
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@app.route('/detect_video_deepfake', methods=['POST', 'OPTIONS'])
def detect_video_endpoint():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Bradley-Extension')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        if not data or not data.get('url_or_path'):
            response = jsonify({'error': 'url_or_path required', 'is_deepfake': False, 'confidence': 0})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        media_url = data.get('url_or_path')
        is_valid, error_msg = validate_media_url(media_url)
        if not is_valid:
            response = jsonify({'error': error_msg, 'is_deepfake': False, 'confidence': 0})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        result = detect_video_deepfake(media_url)
        
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({'error': str(e), 'is_deepfake': False, 'confidence': 0})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@app.route('/detect_audio_deepfake', methods=['POST', 'OPTIONS'])
def detect_audio_endpoint():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Bradley-Extension')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        if not data or not data.get('url_or_path'):
            response = jsonify({'error': 'url_or_path required', 'is_deepfake': False, 'confidence': 0})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        media_url = data.get('url_or_path')
        is_valid, error_msg = validate_media_url(media_url)
        if not is_valid:
            response = jsonify({'error': error_msg, 'is_deepfake': False, 'confidence': 0})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        result = detect_audio_deepfake(media_url)
        
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({'error': str(e), 'is_deepfake': False, 'confidence': 0})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@app.after_request
def add_security_headers(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
    
    response.headers.update({
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Cache-Control': 'no-store',
        'Pragma': 'no-cache',
        'Expires': '0',
    })
    return response


@app.route('/api/nodes/pending', methods=['GET'])
def get_pending_nodes():
    if not firestore_db:
        return jsonify({'error': 'Firestore not configured', 'nodes': []}), 503
    
    try:
        nodes_ref = firestore_db.collection('pendingNodes')
        docs = nodes_ref.where('status', '==', 'pending').stream()
        
        nodes = []
        for doc in docs:
            node_data = doc.to_dict()
            node_data['id'] = doc.id
            nodes.append(node_data)
        
        return jsonify({'nodes': nodes, 'count': len(nodes)})
    except Exception as e:
        return jsonify({'error': str(e), 'nodes': []}), 500


@app.route('/api/nodes/submit', methods=['POST', 'OPTIONS'])
def submit_node_request():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    if not firestore_db:
        response = jsonify({'error': 'Firestore not configured', 'success': False})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 503
    
    try:
        data = request.get_json()
        if not data:
            response = jsonify({'error': 'JSON body required', 'success': False})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        wallet = data.get('wallet', '').strip()
        email = data.get('email', '').strip()
        
        if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
            response = jsonify({'error': 'Valid Ethereum wallet address required', 'success': False})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        node_data = {
            'wallet': wallet.lower(),
            'email': email if email else None,
            'status': 'pending',
            'submittedAt': firestore.SERVER_TIMESTAMP,
            'source': 'web'
        }
        
        doc_ref = firestore_db.collection('pendingNodes').document(wallet.lower())
        doc_ref.set(node_data, merge=True)
        
        response = jsonify({
            'success': True,
            'message': 'Node request submitted! You will be notified when approved.',
            'wallet': wallet.lower()
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({'error': str(e), 'success': False})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@app.route('/api/nodes/approve', methods=['POST'])
@require_admin_auth
def approve_node():
    if not firestore_db:
        return jsonify({'error': 'Firestore not configured', 'success': False}), 503
    
    try:
        data = request.get_json()
        wallet = data.get('wallet', '').strip().lower()
        
        if not wallet:
            return jsonify({'error': 'Wallet address required', 'success': False}), 400
        
        doc_ref = firestore_db.collection('pendingNodes').document(wallet)
        doc_ref.update({
            'status': 'approved',
            'approvedAt': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'success': True, 'message': f'Node {wallet} approved!'})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


init_firebase()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
