import os
import sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac', 'm4a'}

db.init_app(app)

from agents.swarm import BradleySwarm
from detection.video_detector import detect_video_deepfake
from detection.audio_detector import detect_audio_deepfake
from relay.node import grid_node, get_registry_stats, add_lounge_node

swarm = BradleySwarm()

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
        'version': 'v0.1.0',
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
def beta_signup_submit():
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    
    try:
        existing = db.session.query(BetaUser).filter_by(email=data['email']).first()
        if existing:
            return jsonify({'error': 'Email already registered'}), 409
        
        user = BetaUser(
            email=data['email'],
            name=data.get('name'),
            referral_source=data.get('referral_source', 'business_lounge'),
            wallet_address=data.get('wallet_address')
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
            return jsonify({'error': 'No data provided'}), 400
        
        media_url = data.get('url')
        media_type = data.get('type', 'video')
        page_url = data.get('page_url', '')
        
        if not media_url:
            return jsonify({'error': 'Media URL required'}), 400
        
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
        return jsonify({'error': str(e), 'is_deepfake': False, 'confidence': 0}), 500


@app.route('/api/report', methods=['POST'])
def report_threat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        print(f"[REPORT] Threat reported: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Threat reported successfully',
            'report_id': grid_node.node_id[:8] + '-' + str(int(datetime.utcnow().timestamp()))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
