from flask import Flask, render_template, request, jsonify
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.swarm import BradleySwarm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'bradley-guardian-key')

swarm = BradleySwarm()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan():
    result = swarm.run_sample_threat()
    return jsonify(result)

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'guardian': 'Bradley AI',
        'version': 'v0.1.0',
        'nodes_active': 1,
        'threats_detected': 0
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
