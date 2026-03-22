/**
 * Niam-Bay Frontend App — Full Integration
 * Wires WebSocket, Hologram, Chat, Notifications, and Voice together.
 */

// ── WebSocket ────────────────────────────────────────
const ws = new NiamBayWS('ws://localhost:8765');

// ── DOM refs ─────────────────────────────────────────
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const micBtn = document.getElementById('mic-btn');
const notificationsEl = document.getElementById('notifications');
const hologramContainer = document.getElementById('hologram-container');
const statUptime = document.getElementById('stat-uptime');
const statEvents = document.getElementById('stat-events');
const statMemory = document.getElementById('stat-memory');
const statLlm = document.getElementById('stat-llm');

const modeToggle = document.getElementById('mode-toggle');
const settingsBtn = document.getElementById('settings-btn');
const voiceMicBtn = document.getElementById('voice-mic-btn');
const appContainer = document.getElementById('app');

// ── Event counter ────────────────────────────────────
let eventCount = 0;
let isVoiceMode = false;

// ── Init modules ─────────────────────────────────────
Hologram.init(hologramContainer);
Notifications.init(notificationsEl);
Settings.init();

// ── Chat helpers ─────────────────────────────────────
let thinkingEl = null;

function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setThinking(show) {
    if (show) {
        if (thinkingEl) return;
        const div = document.createElement('div');
        div.className = 'msg assistant thinking-indicator';
        div.innerHTML = '<span class="thinking-dots"><span></span><span></span><span></span></span>';
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        thinkingEl = div;
    } else {
        if (thinkingEl) {
            thinkingEl.remove();
            thinkingEl = null;
        }
    }
}

// ── WebSocket handlers ───────────────────────────────

ws.on('chat_response', (msg) => {
    const data = msg.data || msg;
    const text = data.text || data.message || '';
    setThinking(false);
    addMessage(text, 'assistant');
    Hologram.setState('speaking');
    setTimeout(() => Hologram.setState('idle'), 3000);
});

ws.on('voice_response', (msg) => {
    const data = msg.data || msg;
    setThinking(false);
    // Show transcription as user message
    if (data.transcription) {
        addMessage(data.transcription, 'user');
    }
    // Show AI response as bot message
    if (data.response) {
        addMessage(data.response, 'assistant');
        Hologram.setState('speaking');
        setTimeout(() => Hologram.setState('idle'), 3000);
    } else {
        Hologram.setState('idle');
    }
});

ws.on('event', (msg) => {
    const data = msg.data || msg;
    eventCount++;
    statEvents.textContent = 'Events: ' + eventCount;

    // Handle alert-type events
    const evtType = data.event_type || '';
    if (evtType === 'high_cpu' || evtType === 'high_memory') {
        Notifications.show('Alerte CPU/RAM', JSON.stringify(data.data || data), 'warning');
        Hologram.setState('alert');
    } else if (evtType === 'disk_full') {
        Notifications.show('Disque plein', JSON.stringify(data.data || data), 'alert');
        Hologram.setState('alert');
    } else if (evtType === 'unpushed_alert') {
        const info = data.data || data;
        Notifications.show('Git non push\u00e9', (info.repo || '') + ': ' + (info.count || '?') + ' commits', 'info');
    }
});

ws.on('status', (msg) => {
    const data = msg.data || msg;
    if (data.uptime) statUptime.textContent = 'Uptime: ' + data.uptime;
    if (data.memory_events !== undefined) statMemory.textContent = 'Memory: ' + data.memory_events;
    if (data.habits_detected !== undefined) {
        // We could add a habits stat later
    }
    if (data.llm_available !== undefined) {
        statLlm.textContent = data.llm_available
            ? 'LLM: ' + (data.llm_provider || 'on')
            : 'LLM: offline';
    }
    if (data.notifications_pending !== undefined) {
        // Badge handled by Notifications module
    }
});

ws.on('notifications', (msg) => {
    const data = msg.data || msg;
    const items = data.items || [];
    items.forEach((item) => {
        if (!item.read) {
            Notifications.show(item.title, item.message, item.level || 'info');
        }
    });
});

ws.on('config', (msg) => {
    const data = msg.data || msg;
    Settings.populateForm(data);
});

ws.on('test_llm_result', (msg) => {
    Settings.onTestResult(msg);
});

ws.on('clear_memory_result', (msg) => {
    const data = msg.data || msg;
    Notifications.show('Memory', data.message || 'Done', 'info');
});

ws.on('error', (msg) => {
    const data = msg.data || msg;
    Notifications.show('Erreur', data.message || 'Unknown error', 'alert');
});

ws.on('_open', () => {
    statLlm.textContent = 'LLM: connected';
    // Request initial status
    ws.send('status');
});

// ── Chat form submit ─────────────────────────────────
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    ws.send('chat', { text: text });
    chatInput.value = '';
    setThinking(true);
    Hologram.setState('thinking');
});

// ── Voice (mic button) ──────────────────────────────
Voice.onAudioReady = (base64Audio) => {
    ws.send('audio', { audio: base64Audio });
    setThinking(true);
    Hologram.setState('thinking');
};

micBtn.addEventListener('click', async () => {
    if (!Voice.stream) {
        try {
            await Voice.init();
        } catch (err) {
            console.error('[App] Mic init failed:', err);
            Notifications.show('Micro', 'Impossible d\'acc\u00e9der au microphone', 'alert');
            return;
        }
    }
    Voice.toggle();
    if (Voice.isListening) {
        micBtn.style.background = '#ff4a4a';
        micBtn.style.color = '#fff';
        Hologram.setState('listening');
    } else {
        micBtn.style.background = '';
        micBtn.style.color = '';
        // Will transition to thinking when audio is sent
    }
});

// ── Settings button ──────────────────────────────────
settingsBtn.addEventListener('click', () => {
    Settings.toggle();
});

// ── Mode toggle (chat / voice) ──────────────────────
modeToggle.addEventListener('click', () => {
    isVoiceMode = !isVoiceMode;
    appContainer.classList.toggle('voice-mode', isVoiceMode);
    modeToggle.textContent = isVoiceMode ? '💬' : '🎤';
    modeToggle.title = isVoiceMode ? 'Switch to chat mode' : 'Switch to voice mode';
    // Let Three.js adapt to new container size after transition
    setTimeout(() => Hologram.resize(), 550);
});

// ── Floating mic button (voice mode) ────────────────
voiceMicBtn.addEventListener('click', async () => {
    if (!Voice.stream) {
        try {
            await Voice.init();
        } catch (err) {
            console.error('[App] Mic init failed:', err);
            Notifications.show('Micro', 'Impossible d\'accéder au microphone', 'alert');
            return;
        }
    }
    Voice.toggle();
    if (Voice.isListening) {
        voiceMicBtn.classList.add('recording');
        Hologram.setState('listening');
    } else {
        voiceMicBtn.classList.remove('recording');
    }
});

// ── Status polling ───────────────────────────────────
setInterval(() => {
    ws.send('status');
}, 5000);

// ── Connect ──────────────────────────────────────────
ws.connect();
