/**
 * Niam-Bay Frontend App
 * Connects WebSocket, binds UI handlers, polls status.
 */

const ws = new NiamBayWS('ws://localhost:8765');

// ── DOM refs ──────────────────────────────────────────
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const notifications = document.getElementById('notifications');
const statUptime = document.getElementById('stat-uptime');
const statEvents = document.getElementById('stat-events');
const statMemory = document.getElementById('stat-memory');
const statLlm = document.getElementById('stat-llm');

// ── Chat helpers ──────────────────────────────────────
function addMessage(text, role = 'assistant') {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showToast(text, duration = 4000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = text;
    notifications.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}

// ── WebSocket handlers ────────────────────────────────
ws.on('chat_response', (data) => {
    addMessage(data.message || data.text, 'assistant');
});

ws.on('event', (data) => {
    if (data.count !== undefined) statEvents.textContent = `Events: ${data.count}`;
});

ws.on('notification', (data) => {
    showToast(data.message || data.text);
});

ws.on('status', (data) => {
    if (data.uptime) statUptime.textContent = `Uptime: ${data.uptime}`;
    if (data.events !== undefined) statEvents.textContent = `Events: ${data.events}`;
    if (data.memory) statMemory.textContent = `Memory: ${data.memory}`;
    if (data.llm) statLlm.textContent = `LLM: ${data.llm}`;
});

ws.on('_open', () => {
    statLlm.textContent = 'LLM: connected';
});

// ── Chat form submit ──────────────────────────────────
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    ws.send('chat', { message: text });
    chatInput.value = '';
});

// ── Status polling ────────────────────────────────────
setInterval(() => {
    ws.send('get_status');
}, 5000);

// ── Connect ───────────────────────────────────────────
ws.connect();
