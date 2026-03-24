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

// Dashboard DOM refs
const dashGridDot = document.getElementById('dash-grid-dot');
const dashGridSol = document.getElementById('dash-grid-sol');
const dashPortfolio = document.getElementById('dash-portfolio');
const dashLastFill = document.getElementById('dash-last-fill');
const dashUptime = document.getElementById('dash-uptime');
const dashBrainNodes = document.getElementById('dash-brain-nodes');

// ── Event counter ────────────────────────────────────
let eventCount = 0;
let isVoiceMode = false;

// ── Init modules ─────────────────────────────────────
Hologram.init(hologramContainer);
Notifications.init(notificationsEl);
Settings.init();

// ── Chat helpers ─────────────────────────────────────
let thinkingEl = null;

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatTimestamp(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function addMessage(text, role) {
    // Remove thinking indicator if present
    if (role === 'assistant') {
        setThinking(false);
    }

    const div = document.createElement('div');
    div.className = 'msg ' + role;

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = escapeHtml(text);

    const ts = document.createElement('div');
    ts.className = 'msg-timestamp';
    ts.textContent = formatTimestamp(new Date());

    div.appendChild(bubble);
    div.appendChild(ts);
    chatMessages.appendChild(div);

    // Auto-scroll with smooth behavior
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

function setThinking(show) {
    if (show) {
        if (thinkingEl) return;
        const div = document.createElement('div');
        div.className = 'msg assistant thinking-indicator';
        div.innerHTML = `
            <div class="msg-bubble">
                <span class="thinking-dots"><span></span><span></span><span></span></span>
            </div>
        `;
        chatMessages.appendChild(div);
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
        thinkingEl = div;
    } else {
        if (thinkingEl) {
            thinkingEl.remove();
            thinkingEl = null;
        }
    }
}

// ── Dashboard updater ────────────────────────────────

function updateDashboard(data) {
    // Uptime
    if (data.uptime) {
        if (dashUptime) dashUptime.textContent = data.uptime;
        if (statUptime) statUptime.textContent = 'Uptime: ' + data.uptime;
    }

    // Brain / memory nodes
    if (data.memory_events !== undefined) {
        if (dashBrainNodes) dashBrainNodes.textContent = data.memory_events;
        if (statMemory) statMemory.textContent = 'Memory: ' + data.memory_events;
    }

    // LLM status
    if (data.llm_available !== undefined) {
        const llmText = data.llm_available
            ? 'LLM: ' + (data.llm_provider || 'on')
            : 'LLM: offline';
        if (statLlm) statLlm.textContent = llmText;
    }

    // System load for hologram breathing (derive from memory_events as a proxy)
    if (data.memory_events !== undefined) {
        const load = Math.min(1.0, data.memory_events / 500);
        Hologram.setSystemLoad(load);
    }
}

function updateGridData(data) {
    // Grid data from trading events
    if (data.grid_dot !== undefined && dashGridDot) {
        dashGridDot.textContent = data.grid_dot + ' RT';
    }
    if (data.grid_sol !== undefined && dashGridSol) {
        dashGridSol.textContent = data.grid_sol + ' RT';
    }
    if (data.portfolio_value !== undefined && dashPortfolio) {
        dashPortfolio.textContent = '$' + Number(data.portfolio_value).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
    if (data.last_fill_time !== undefined && dashLastFill) {
        const d = new Date(data.last_fill_time);
        dashLastFill.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
    if (data.transcription) {
        addMessage(data.transcription, 'user');
    }
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

    const evtType = data.event_type || '';

    // Trading / grid events — update dashboard
    if (evtType === 'grid_update' || evtType === 'trading_update') {
        updateGridData(data.data || data);
    }

    // Handle alert-type events
    if (evtType === 'high_cpu' || evtType === 'high_memory') {
        Notifications.show('Alerte CPU/RAM', JSON.stringify(data.data || data), 'warning');
        Hologram.setState('alert');
        Hologram.notificationPulse();
    } else if (evtType === 'disk_full') {
        Notifications.show('Disque plein', JSON.stringify(data.data || data), 'alert');
        Hologram.setState('alert');
        Hologram.notificationPulse();
    } else if (evtType === 'unpushed_alert') {
        const info = data.data || data;
        Notifications.show('Git non push\u00e9', (info.repo || '') + ': ' + (info.count || '?') + ' commits', 'info');
        Hologram.notificationPulse();
    }
});

ws.on('status', (msg) => {
    const data = msg.data || msg;
    updateDashboard(data);
});

ws.on('notifications', (msg) => {
    const data = msg.data || msg;
    const items = data.items || [];
    items.forEach((item) => {
        if (!item.read) {
            Notifications.show(item.title, item.message, item.level || 'info');
            Hologram.notificationPulse();
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
    Hologram.notificationPulse();
});

ws.on('_open', () => {
    statLlm.textContent = 'LLM: connected';
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
    modeToggle.textContent = isVoiceMode ? '\uD83D\uDCAC' : '\uD83C\uDFA4';
    modeToggle.title = isVoiceMode ? 'Switch to chat mode' : 'Switch to voice mode';
    setTimeout(() => Hologram.resize(), 550);
});

// ── Floating mic button (voice mode) ────────────────
voiceMicBtn.addEventListener('click', async () => {
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
