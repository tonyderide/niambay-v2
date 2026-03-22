/**
 * Niam-Bay WebSocket client
 * Handles connection, auto-reconnect, and message dispatch.
 */
class NiamBayWS {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.handlers = {};
        this.reconnectDelay = 1000;
        this._maxReconnectDelay = 30000;
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('[NiamBayWS] connected');
            this.reconnectDelay = 1000;
            if (this.handlers['_open']) this.handlers['_open']();
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                const handler = this.handlers[msg.type];
                if (handler) {
                    handler(msg);
                } else {
                    console.log('[NiamBayWS] unhandled type:', msg.type);
                }
            } catch (err) {
                console.error('[NiamBayWS] parse error:', err);
            }
        };

        this.ws.onclose = () => {
            console.log(`[NiamBayWS] disconnected, retrying in ${this.reconnectDelay}ms`);
            setTimeout(() => this.connect(), this.reconnectDelay);
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, this._maxReconnectDelay);
        };

        this.ws.onerror = (err) => {
            console.error('[NiamBayWS] error:', err);
            this.ws.close();
        };
    }

    on(type, handler) {
        this.handlers[type] = handler;
    }

    send(type, data = {}) {
        if (this.connected) {
            this.ws.send(JSON.stringify({ type, ...data }));
        } else {
            console.warn('[NiamBayWS] not connected, message dropped');
        }
    }

    get connected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}
