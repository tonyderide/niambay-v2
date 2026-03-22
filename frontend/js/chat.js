const Chat = {
    container: null,
    messagesEl: null,
    inputEl: null,
    sendBtn: null,
    thinkingEl: null,
    onSend: null,

    init(container, onSend) {
        this.container = container;
        this.onSend = onSend;

        this.container.style.cssText = `
            display:flex; flex-direction:column; height:100%;
            background:#0a0a1a; border:1px solid #1a1a3a; border-radius:8px;
            overflow:hidden; font-family:'Segoe UI',system-ui,sans-serif;
        `;

        // Messages area
        this.messagesEl = document.createElement('div');
        this.messagesEl.style.cssText = `
            flex:1; overflow-y:auto; padding:16px; display:flex;
            flex-direction:column; gap:8px;
        `;
        this.messagesEl.classList.add('chat-messages');

        // Input row
        const inputRow = document.createElement('div');
        inputRow.style.cssText = `
            display:flex; gap:8px; padding:12px; border-top:1px solid #1a1a3a;
            background:#0d0d22;
        `;

        this.inputEl = document.createElement('input');
        this.inputEl.type = 'text';
        this.inputEl.placeholder = 'Type a message...';
        this.inputEl.style.cssText = `
            flex:1; padding:10px 14px; border:1px solid #2a2a4a; border-radius:6px;
            background:#12122a; color:#e0e0f0; font-size:14px; outline:none;
            transition:border-color 0.2s;
        `;
        this.inputEl.addEventListener('focus', () => {
            this.inputEl.style.borderColor = '#4a7aff';
        });
        this.inputEl.addEventListener('blur', () => {
            this.inputEl.style.borderColor = '#2a2a4a';
        });
        this.inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && this.inputEl.value.trim()) {
                this._send();
            }
        });

        this.sendBtn = document.createElement('button');
        this.sendBtn.textContent = 'Send';
        this.sendBtn.style.cssText = `
            padding:10px 20px; border:none; border-radius:6px;
            background:#4a7aff; color:#fff; font-size:14px; font-weight:600;
            cursor:pointer; transition:background 0.2s, transform 0.1s;
        `;
        this.sendBtn.addEventListener('mouseenter', () => {
            this.sendBtn.style.background = '#5a8aff';
        });
        this.sendBtn.addEventListener('mouseleave', () => {
            this.sendBtn.style.background = '#4a7aff';
        });
        this.sendBtn.addEventListener('mousedown', () => {
            this.sendBtn.style.transform = 'scale(0.96)';
        });
        this.sendBtn.addEventListener('mouseup', () => {
            this.sendBtn.style.transform = 'scale(1)';
        });
        this.sendBtn.addEventListener('click', () => {
            if (this.inputEl.value.trim()) this._send();
        });

        inputRow.appendChild(this.inputEl);
        inputRow.appendChild(this.sendBtn);
        this.container.appendChild(this.messagesEl);
        this.container.appendChild(inputRow);

        // Inject keyframe animation once
        if (!document.getElementById('chat-anim-style')) {
            const style = document.createElement('style');
            style.id = 'chat-anim-style';
            style.textContent = `
                @keyframes chatMsgIn {
                    from { opacity:0; transform:translateY(10px); }
                    to   { opacity:1; transform:translateY(0); }
                }
                @keyframes chatDots {
                    0%,80%,100% { transform:scale(0); }
                    40% { transform:scale(1); }
                }
                .chat-messages::-webkit-scrollbar { width:6px; }
                .chat-messages::-webkit-scrollbar-track { background:transparent; }
                .chat-messages::-webkit-scrollbar-thumb { background:#2a2a4a; border-radius:3px; }
            `;
            document.head.appendChild(style);
        }
    },

    _send() {
        const text = this.inputEl.value.trim();
        if (!text) return;
        this.addMessage(text, 'user');
        this.inputEl.value = '';
        if (typeof this.onSend === 'function') {
            this.onSend(text);
        }
    },

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    addMessage(text, sender, timestamp) {
        const ts = timestamp || new Date();
        const timeStr = ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const isUser = sender === 'user';

        const wrapper = document.createElement('div');
        wrapper.style.cssText = `
            display:flex; justify-content:${isUser ? 'flex-end' : 'flex-start'};
            animation:chatMsgIn 0.3s ease-out;
        `;

        const bubble = document.createElement('div');
        bubble.style.cssText = `
            max-width:75%; padding:10px 14px; border-radius:12px;
            font-size:14px; line-height:1.5; word-wrap:break-word;
            ${isUser
                ? 'background:#4a7aff; color:#fff; border-bottom-right-radius:4px;'
                : 'background:#12122a; color:#d0d0e8; border:1px solid #2a6a4a; border-bottom-left-radius:4px;'
            }
        `;
        bubble.innerHTML = `
            <div>${this._escapeHtml(text)}</div>
            <div style="font-size:11px; opacity:0.6; margin-top:4px; text-align:${isUser ? 'right' : 'left'}">
                ${timeStr}
            </div>
        `;

        wrapper.appendChild(bubble);
        this.messagesEl.appendChild(wrapper);
        this._scrollToBottom();
    },

    setThinking(show) {
        if (show) {
            if (this.thinkingEl) return;
            const wrapper = document.createElement('div');
            wrapper.style.cssText = 'display:flex; justify-content:flex-start; animation:chatMsgIn 0.3s ease-out;';
            this.thinkingEl = wrapper;

            const bubble = document.createElement('div');
            bubble.style.cssText = `
                padding:12px 18px; border-radius:12px; background:#12122a;
                border:1px solid #2a6a4a; border-bottom-left-radius:4px;
                display:flex; gap:5px; align-items:center;
            `;
            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('span');
                dot.style.cssText = `
                    width:8px; height:8px; border-radius:50%; background:#4a7aff;
                    display:inline-block; animation:chatDots 1.4s infinite ease-in-out both;
                    animation-delay:${i * 0.16}s;
                `;
                bubble.appendChild(dot);
            }
            wrapper.appendChild(bubble);
            this.messagesEl.appendChild(wrapper);
            this._scrollToBottom();
        } else {
            if (this.thinkingEl) {
                this.thinkingEl.remove();
                this.thinkingEl = null;
            }
        }
    },

    clear() {
        this.messagesEl.innerHTML = '';
        this.thinkingEl = null;
    },

    _scrollToBottom() {
        requestAnimationFrame(() => {
            this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        });
    }
};
