document.addEventListener('DOMContentLoaded', function() {
    fetchStatus();
    setInterval(fetchStatus, 10000);
});

function fetchStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('guardian-status').textContent = data.status.toUpperCase();
            document.getElementById('version').textContent = data.version;
            document.getElementById('nodes-count').textContent = data.nodes_active;
            document.getElementById('threats-count').textContent = data.threats_detected;
        })
        .catch(error => {
            console.error('Status fetch error:', error);
        });
}

function runScan() {
    const terminal = document.getElementById('terminal');
    const button = document.querySelector('.scan-button');
    
    button.disabled = true;
    button.querySelector('.button-text').textContent = 'SCANNING...';
    
    addTerminalLine('[SCAN]', 'Initiating threat scan...', false);
    
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
        
        button.disabled = false;
        button.querySelector('.button-text').textContent = 'INITIATE SCAN';
    })
    .catch(error => {
        addTerminalLine('[ERROR]', 'Scan failed: ' + error.message, true);
        button.disabled = false;
        button.querySelector('.button-text').textContent = 'INITIATE SCAN';
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
