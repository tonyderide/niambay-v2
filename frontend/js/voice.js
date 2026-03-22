/**
 * Niam-Bay Voice Module
 * Browser-side mic capture via MediaRecorder API.
 * Sends base64-encoded audio chunks to the daemon over WebSocket.
 */

const Voice = {
    mediaRecorder: null,
    chunks: [],
    stream: null,
    isListening: false,
    silenceTimer: null,
    onAudioReady: null, // callback(base64AudioData)

    async init() {
        // Request mic permission
        this.stream = await navigator.mediaDevices.getUserMedia({
            audio: { sampleRate: 16000, channelCount: 1 },
        });
    },

    startListening() {
        this.chunks = [];
        this.isListening = true;
        this.mediaRecorder = new MediaRecorder(this.stream, {
            mimeType: 'audio/webm',
        });
        this.mediaRecorder.ondataavailable = (e) => this.chunks.push(e.data);
        this.mediaRecorder.onstop = () => this._processAudio();
        this.mediaRecorder.start(500); // 500ms chunks

        // Auto-stop after 15s max
        this.silenceTimer = setTimeout(() => this.stopListening(), 15000);
    },

    stopListening() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
        this.isListening = false;
        clearTimeout(this.silenceTimer);
    },

    toggle() {
        if (this.isListening) this.stopListening();
        else this.startListening();
    },

    async _processAudio() {
        const blob = new Blob(this.chunks, { type: 'audio/webm' });
        const buffer = await blob.arrayBuffer();
        const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
        if (this.onAudioReady) this.onAudioReady(base64);
    },
};
