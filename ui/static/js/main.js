let currentUploadType = null;

document.addEventListener('DOMContentLoaded', function() {
    fetchStatus();
    setInterval(fetchStatus, 10000);
    
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
});

function fetchStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('guardian-status').textContent = data.status.toUpperCase();
            document.getElementById('version').textContent = data.version;
            if (document.getElementById('node-id')) {
                document.getElementById('node-id').textContent = data.node_id || '...';
            }
            document.getElementById('threats-count').textContent = data.threats_detected;
        })
        .catch(error => {
            console.error('Status fetch error:', error);
        });
}

function openUpload(type) {
    currentUploadType = type;
    const panel = document.getElementById('upload-panel');
    const title = document.getElementById('upload-title');
    const formats = document.getElementById('upload-formats');
    const fileInput = document.getElementById('file-input');
    
    if (type === 'video') {
        title.textContent = 'UPLOAD VIDEO FOR ANALYSIS';
        formats.textContent = 'Supported: MP4, AVI, MOV, MKV, WebM';
        fileInput.accept = '.mp4,.avi,.mov,.mkv,.webm';
    } else {
        title.textContent = 'UPLOAD AUDIO FOR ANALYSIS';
        formats.textContent = 'Supported: WAV, MP3, OGG, FLAC, M4A';
        fileInput.accept = '.wav,.mp3,.ogg,.flac,.m4a';
    }
    
    panel.style.display = 'block';
    document.getElementById('upload-progress').style.display = 'none';
}

function closeUpload() {
    document.getElementById('upload-panel').style.display = 'none';
    document.getElementById('file-input').value = '';
    currentUploadType = null;
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    uploadFile(file);
}

async function uploadFile(file) {
    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressDiv.style.display = 'block';
    progressFill.style.width = '10%';
    progressText.textContent = 'Uploading...';
    
    addTerminalLine('[UPLOAD]', `Receiving file: ${file.name}`, false);
    
    const formData = new FormData();
    formData.append('file', file);
    
    const endpoint = currentUploadType === 'video' ? '/api/analyze/video' : '/api/analyze/audio';
    
    try {
        progressFill.style.width = '30%';
        progressText.textContent = 'Analyzing...';
        
        addTerminalLine('[SCAN]', `Initiating ${currentUploadType} analysis...`, false);
        
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        progressFill.style.width = '80%';
        
        const data = await response.json();
        
        progressFill.style.width = '100%';
        progressText.textContent = 'Complete!';
        
        if (data.error) {
            addTerminalLine('[ERROR]', data.error, true);
        } else {
            const threatStatus = data.is_deepfake ? 'THREAT DETECTED' : 'AUTHENTIC';
            const confidence = (data.confidence * 100).toFixed(1);
            addTerminalLine(`[${currentUploadType.toUpperCase()}]`, `Analysis: ${threatStatus} (${confidence}% confidence)`, data.is_deepfake);
            
            if (data.analysis_type === 'full') {
                addTerminalLine('[DETAIL]', `Model score: ${(data.model_score * 100).toFixed(1)}%, Artifact score: ${((data.artifact_score || 0) * 100).toFixed(1)}%`, false);
            }
        }
        
        setTimeout(() => {
            closeUpload();
            fetchStatus();
        }, 1500);
        
    } catch (error) {
        progressText.textContent = 'Error!';
        addTerminalLine('[ERROR]', `Upload failed: ${error.message}`, true);
    }
}

function runScan() {
    const button = document.querySelector('.scan-button');
    
    button.disabled = true;
    button.querySelector('.button-text').textContent = 'SCANNING...';
    
    addTerminalLine('[SCAN]', 'Initiating demo threat scan...', false);
    
    fetch('/api/scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.video_result) {
            const videoMsg = `Video analysis: ${data.video_result.is_deepfake ? 'DEEPFAKE DETECTED' : 'AUTHENTIC'} (${(data.video_result.confidence * 100).toFixed(1)}% confidence)`;
            addTerminalLine('[VIDEO]', videoMsg, data.video_result.is_deepfake);
        }
        
        if (data.audio_result) {
            const audioMsg = `Audio analysis: ${data.audio_result.is_deepfake ? 'VOICE CLONE DETECTED' : 'AUTHENTIC'} (${(data.audio_result.confidence * 100).toFixed(1)}% confidence)`;
            addTerminalLine('[AUDIO]', audioMsg, data.audio_result.is_deepfake);
        }
        
        if (data.relay_status) {
            addTerminalLine('[RELAY]', data.relay_status, false);
        }
        
        addTerminalLine('[SCAN]', 'Scan complete. Bradley AI standing by.', false);
        
        fetchStatus();
        
        button.disabled = false;
        button.querySelector('.button-text').textContent = 'DEMO SCAN';
    })
    .catch(error => {
        addTerminalLine('[ERROR]', 'Scan failed: ' + error.message, true);
        button.disabled = false;
        button.querySelector('.button-text').textContent = 'DEMO SCAN';
    });
}

function addTerminalLine(timestamp, message, isThreat) {
    const terminal = document.getElementById('terminal');
    const line = document.createElement('div');
    line.className = 'terminal-line' + (isThreat ? ' threat' : '');
    line.innerHTML = `
        <span class="timestamp">${timestamp}</span>
        <span class="message">${message}</span>
    `;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}
