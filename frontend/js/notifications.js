const Notifications = {
    container: null,
    badge: null,
    count: 0,

    init(container) {
        this.container = container;
        this.container.style.cssText = `
            position:fixed; top:16px; right:16px; z-index:9999;
            display:flex; flex-direction:column; gap:8px;
            pointer-events:none; max-width:360px; width:100%;
            font-family:'Segoe UI',system-ui,sans-serif;
        `;

        // Badge
        this.badge = document.createElement('div');
        this.badge.style.cssText = `
            position:fixed; top:16px; right:16px; z-index:10000;
            min-width:22px; height:22px; border-radius:11px;
            background:#ff4a6a; color:#fff; font-size:12px; font-weight:700;
            display:none; align-items:center; justify-content:center;
            padding:0 6px; pointer-events:none;
            box-shadow:0 2px 8px rgba(255,74,106,0.4);
        `;
        document.body.appendChild(this.badge);

        // Inject animations once
        if (!document.getElementById('notif-anim-style')) {
            const style = document.createElement('style');
            style.id = 'notif-anim-style';
            style.textContent = `
                @keyframes notifSlideIn {
                    from { opacity:0; transform:translateX(100%); }
                    to   { opacity:1; transform:translateX(0); }
                }
                @keyframes notifSlideOut {
                    from { opacity:1; transform:translateX(0); }
                    to   { opacity:0; transform:translateX(100%); }
                }
            `;
            document.head.appendChild(style);
        }
    },

    show(title, message, level) {
        const colors = {
            info:    { bg: '#111133', border: '#4a7aff', accent: '#4a7aff' },
            warning: { bg: '#1a1508', border: '#ff9a2a', accent: '#ff9a2a' },
            alert:   { bg: '#1a0a0a', border: '#ff4a4a', accent: '#ff4a4a' }
        };
        const c = colors[level] || colors.info;

        const toast = document.createElement('div');
        toast.style.cssText = `
            background:${c.bg}; border:1px solid ${c.border}; border-left:4px solid ${c.border};
            border-radius:8px; padding:12px 16px; pointer-events:auto; cursor:pointer;
            animation:notifSlideIn 0.35s ease-out; box-shadow:0 4px 20px rgba(0,0,0,0.5);
            transition:opacity 0.3s, transform 0.3s;
        `;

        const titleEl = document.createElement('div');
        titleEl.style.cssText = `
            font-size:13px; font-weight:700; color:${c.accent}; margin-bottom:4px;
            text-transform:uppercase; letter-spacing:0.5px;
        `;
        titleEl.textContent = title;

        const msgEl = document.createElement('div');
        msgEl.style.cssText = 'font-size:13px; color:#c0c0d8; line-height:1.4;';
        msgEl.textContent = message;

        toast.appendChild(titleEl);
        toast.appendChild(msgEl);
        this.container.appendChild(toast);

        // Click to dismiss
        const dismiss = () => {
            toast.style.animation = 'notifSlideOut 0.3s ease-in forwards';
            toast.addEventListener('animationend', () => {
                toast.remove();
            }, { once: true });
        };
        toast.addEventListener('click', dismiss);

        // Auto-dismiss after 5s
        setTimeout(dismiss, 5000);

        // Sound on alert
        if (level === 'alert' && typeof AudioContext !== 'undefined') {
            try {
                const ctx = new AudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = 800;
                gain.gain.value = 0.1;
                osc.start();
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
                osc.stop(ctx.currentTime + 0.3);
            } catch (_) {
                // Audio not available, silent fallback
            }
        }

        this.count++;
        this.updateBadge();
    },

    updateBadge() {
        if (this.count > 0) {
            this.badge.style.display = 'flex';
            this.badge.textContent = this.count > 99 ? '99+' : String(this.count);
        } else {
            this.badge.style.display = 'none';
        }
    },

    clear() {
        this.count = 0;
        this.updateBadge();
        // Remove all toasts
        while (this.container.firstChild) {
            this.container.removeChild(this.container.firstChild);
        }
    }
};
