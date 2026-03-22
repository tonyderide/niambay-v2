/**
 * Niam-Bay Settings Panel
 * Configures LLM, observation, MCP, voice, privacy, and appearance.
 */
const Settings = {
    panel: null,
    overlay: null,
    visible: false,
    config: {},

    init() {
        this._createDOM();
    },

    toggle() {
        this.visible = !this.visible;
        this.overlay.style.display = this.visible ? 'flex' : 'none';
        if (this.visible) this.loadConfig();
    },

    loadConfig() {
        ws.send('config_get');
    },

    populateForm(config) {
        this.config = config;
        const f = this.panel;

        // LLM
        const providerSel = f.querySelector('#s-llm-provider');
        if (providerSel) providerSel.value = config.llm_provider || 'ollama';
        this._setVal('#s-llm-model', config.llm_model || '');
        this._setVal('#s-llm-url', config.llm_url || '');
        this._setVal('#s-llm-api-key', config.llm_api_key || '');
        this._setVal('#s-groq-api-key', config.groq_api_key || '');
        this._setVal('#s-gemini-api-key', config.gemini_api_key || '');
        this._setChecked('#s-use-cascade', config.use_cascade !== false);

        // Observation
        this._setChecked('#s-obs-windows', config.observe_windows !== false);
        this._setChecked('#s-obs-processes', config.observe_processes !== false);
        this._setChecked('#s-obs-git', config.observe_git !== false);
        this._setChecked('#s-obs-clipboard', config.observe_clipboard || false);
        this._setChecked('#s-obs-browser', config.observe_browser || false);
        this._setChecked('#s-obs-screen', config.observe_screen !== false);
        this._setVal('#s-screen-interval', config.screen_interval || 30);
        const screenIntervalLabel = f.querySelector('#s-screen-interval-val');
        if (screenIntervalLabel) screenIntervalLabel.textContent = (config.screen_interval || 30) + 's';
        this._setVal('#s-collect-interval', config.collect_interval || 2);
        const intervalLabel = f.querySelector('#s-collect-interval-val');
        if (intervalLabel) intervalLabel.textContent = (config.collect_interval || 2) + 's';
        this._setChecked('#s-paused', config.paused || false);

        // MCP
        this._setChecked('#s-mcp-gmail', config.mcp_gmail_enabled || false);
        this._setChecked('#s-mcp-calendar', config.mcp_calendar_enabled || false);
        this._setVal('#s-mcp-custom', this._parseMcpCustom(config.mcp_custom_commands));

        // Voice
        const whisperSel = f.querySelector('#s-whisper-model');
        if (whisperSel) whisperSel.value = config.whisper_model || 'base';
        const langSel = f.querySelector('#s-voice-lang');
        if (langSel) langSel.value = config.voice_language || 'fr';
        this._setVal('#s-tts-voice', config.tts_voice || 'default');
        this._setVal('#s-tts-speed', config.tts_speed || 1.0);
        const speedLabel = f.querySelector('#s-tts-speed-val');
        if (speedLabel) speedLabel.textContent = (config.tts_speed || 1.0) + 'x';

        // Privacy
        this._setChecked('#s-do-not-observe', config.do_not_observe || false);

        // Appearance
        this._setVal('#s-holo-color', config.hologram_color || '#4fc3f7');
        this._setVal('#s-anim-speed', config.animation_speed || 1.0);
        const animLabel = f.querySelector('#s-anim-speed-val');
        if (animLabel) animLabel.textContent = (config.animation_speed || 1.0) + 'x';
    },

    saveConfig() {
        const f = this.panel;
        const data = {
            llm_provider: this._getVal('#s-llm-provider'),
            llm_model: this._getVal('#s-llm-model'),
            llm_url: this._getVal('#s-llm-url'),
            llm_api_key: this._getVal('#s-llm-api-key'),
            groq_api_key: this._getVal('#s-groq-api-key'),
            gemini_api_key: this._getVal('#s-gemini-api-key'),
            use_cascade: this._getChecked('#s-use-cascade'),
            observe_windows: this._getChecked('#s-obs-windows'),
            observe_processes: this._getChecked('#s-obs-processes'),
            observe_git: this._getChecked('#s-obs-git'),
            observe_clipboard: this._getChecked('#s-obs-clipboard'),
            observe_browser: this._getChecked('#s-obs-browser'),
            observe_screen: this._getChecked('#s-obs-screen'),
            screen_interval: parseInt(this._getVal('#s-screen-interval')) || 30,
            collect_interval: parseFloat(this._getVal('#s-collect-interval')) || 2,
            paused: this._getChecked('#s-paused'),
            mcp_gmail_enabled: this._getChecked('#s-mcp-gmail'),
            mcp_calendar_enabled: this._getChecked('#s-mcp-calendar'),
            mcp_custom_commands: JSON.stringify(this._getVal('#s-mcp-custom').split('\n').filter(Boolean)),
            whisper_model: this._getVal('#s-whisper-model'),
            voice_language: this._getVal('#s-voice-lang'),
            tts_voice: this._getVal('#s-tts-voice'),
            tts_speed: parseFloat(this._getVal('#s-tts-speed')) || 1.0,
            do_not_observe: this._getChecked('#s-do-not-observe'),
            hologram_color: this._getVal('#s-holo-color'),
            animation_speed: parseFloat(this._getVal('#s-anim-speed')) || 1.0,
        };
        ws.send('config_set', { data });
        this.toggle();
    },

    testLLM() {
        const resultEl = this.panel.querySelector('#s-test-result');
        if (resultEl) {
            resultEl.textContent = 'Testing...';
            resultEl.className = 'settings-test-result testing';
        }
        ws.send('test_llm');
    },

    onTestResult(msg) {
        const data = msg.data || msg;
        const resultEl = this.panel ? this.panel.querySelector('#s-test-result') : null;
        if (!resultEl) return;
        if (data.success) {
            resultEl.textContent = 'OK — ' + (data.model || '') + ' (' + (data.latency_ms || '?') + 'ms)';
            resultEl.className = 'settings-test-result success';
        } else {
            resultEl.textContent = 'Error: ' + (data.message || 'unknown');
            resultEl.className = 'settings-test-result error';
        }
    },

    clearMemory() {
        if (confirm('Clear all brain memory? This cannot be undone.')) {
            ws.send('clear_memory');
        }
    },

    exportBrain() {
        const blob = new Blob([JSON.stringify(this.config, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'niambay-config-export.json';
        a.click();
        URL.revokeObjectURL(url);
    },

    // ── Helpers ──

    _setVal(sel, val) {
        const el = this.panel.querySelector(sel);
        if (el) el.value = val;
    },
    _getVal(sel) {
        const el = this.panel.querySelector(sel);
        return el ? el.value : '';
    },
    _setChecked(sel, val) {
        const el = this.panel.querySelector(sel);
        if (el) el.checked = val;
    },
    _getChecked(sel) {
        const el = this.panel.querySelector(sel);
        return el ? el.checked : false;
    },
    _parseMcpCustom(val) {
        try {
            return JSON.parse(val || '[]').join('\n');
        } catch { return ''; }
    },

    // ── DOM creation ──

    _createDOM() {
        // Overlay
        this.overlay = document.createElement('div');
        this.overlay.id = 'settings-overlay';
        this.overlay.style.display = 'none';
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.toggle();
        });

        // Panel
        this.panel = document.createElement('div');
        this.panel.id = 'settings-panel';
        this.panel.innerHTML = `
            <div class="settings-header">
                <h2>Settings</h2>
                <button class="settings-close" id="s-close">&times;</button>
            </div>
            <div class="settings-body">

                <section class="settings-section">
                    <h3>LLM Provider</h3>
                    <label>Provider
                        <select id="s-llm-provider">
                            <option value="ollama">Ollama (local)</option>
                            <option value="anthropic">Anthropic (Claude)</option>
                            <option value="groq">Groq (Llama)</option>
                            <option value="google">Google (Gemini)</option>
                            <option value="openai">OpenAI (GPT)</option>
                        </select>
                    </label>
                    <label>Model name
                        <input type="text" id="s-llm-model" placeholder="niambay2">
                    </label>
                    <label>API URL (Ollama)
                        <input type="text" id="s-llm-url" placeholder="http://localhost:11434">
                    </label>
                    <label>API Key (Anthropic)
                        <input type="password" id="s-llm-api-key" placeholder="sk-...">
                    </label>
                    <label>Groq API Key
                        <input type="password" id="s-groq-api-key" placeholder="gsk_...">
                    </label>
                    <label>Gemini API Key
                        <input type="password" id="s-gemini-api-key" placeholder="AIza...">
                    </label>
                    <label class="settings-toggle"><input type="checkbox" id="s-use-cascade"> Cascade mode (try all providers)</label>
                    <div class="settings-row">
                        <button class="settings-btn" id="s-test-btn">Test LLM</button>
                        <span id="s-test-result" class="settings-test-result"></span>
                    </div>
                </section>

                <section class="settings-section">
                    <h3>Observation</h3>
                    <label class="settings-toggle"><input type="checkbox" id="s-obs-windows"> Monitor windows</label>
                    <label class="settings-toggle"><input type="checkbox" id="s-obs-processes"> Monitor processes</label>
                    <label class="settings-toggle"><input type="checkbox" id="s-obs-git"> Monitor git</label>
                    <label class="settings-toggle"><input type="checkbox" id="s-obs-clipboard"> Monitor clipboard</label>
                    <label class="settings-toggle"><input type="checkbox" id="s-obs-browser"> Monitor browser</label>
                    <label class="settings-toggle"><input type="checkbox" id="s-obs-screen"> Screen capture</label>
                    <label>Screen interval: <span id="s-screen-interval-val">30s</span>
                        <input type="range" id="s-screen-interval" min="10" max="120" step="5" value="30">
                    </label>
                    <label>Collect interval: <span id="s-collect-interval-val">2s</span>
                        <input type="range" id="s-collect-interval" min="1" max="10" step="0.5" value="2">
                    </label>
                    <label class="settings-toggle"><input type="checkbox" id="s-paused"> Pause all observation</label>
                </section>

                <section class="settings-section">
                    <h3>MCP Connectors</h3>
                    <div class="settings-mcp-row">
                        <label class="settings-toggle"><input type="checkbox" id="s-mcp-gmail"> Gmail</label>
                        <span class="mcp-status" id="s-mcp-gmail-status"></span>
                    </div>
                    <div class="settings-mcp-row">
                        <label class="settings-toggle"><input type="checkbox" id="s-mcp-calendar"> Calendar</label>
                        <span class="mcp-status" id="s-mcp-calendar-status"></span>
                    </div>
                    <label>Custom MCP commands (one per line)
                        <textarea id="s-mcp-custom" rows="3" placeholder='npx @anthropic/mcp-gmail'></textarea>
                    </label>
                </section>

                <section class="settings-section">
                    <h3>Voice</h3>
                    <label>Whisper model
                        <select id="s-whisper-model">
                            <option value="base">base</option>
                            <option value="small">small</option>
                            <option value="medium">medium</option>
                        </select>
                    </label>
                    <label>Language
                        <select id="s-voice-lang">
                            <option value="fr">French</option>
                            <option value="en">English</option>
                            <option value="es">Spanish</option>
                            <option value="de">German</option>
                        </select>
                    </label>
                    <label>TTS Voice
                        <input type="text" id="s-tts-voice" placeholder="default">
                    </label>
                    <label>TTS Speed: <span id="s-tts-speed-val">1.0x</span>
                        <input type="range" id="s-tts-speed" min="0.5" max="2.0" step="0.1" value="1.0">
                    </label>
                </section>

                <section class="settings-section">
                    <h3>Privacy</h3>
                    <label class="settings-toggle"><input type="checkbox" id="s-do-not-observe"> Do not observe mode</label>
                    <div class="settings-row">
                        <button class="settings-btn danger" id="s-clear-memory">Clear brain memory</button>
                        <button class="settings-btn" id="s-export-brain">Export brain data</button>
                    </div>
                </section>

                <section class="settings-section">
                    <h3>Appearance</h3>
                    <label>Hologram color
                        <input type="color" id="s-holo-color" value="#4fc3f7">
                    </label>
                    <label>Animation speed: <span id="s-anim-speed-val">1.0x</span>
                        <input type="range" id="s-anim-speed" min="0.2" max="3.0" step="0.1" value="1.0">
                    </label>
                </section>
            </div>
            <div class="settings-footer">
                <button class="settings-btn" id="s-cancel">Cancel</button>
                <button class="settings-btn primary" id="s-save">Save</button>
            </div>
        `;

        this.overlay.appendChild(this.panel);
        document.body.appendChild(this.overlay);

        // Wire events
        this.panel.querySelector('#s-close').addEventListener('click', () => this.toggle());
        this.panel.querySelector('#s-cancel').addEventListener('click', () => this.toggle());
        this.panel.querySelector('#s-save').addEventListener('click', () => this.saveConfig());
        this.panel.querySelector('#s-test-btn').addEventListener('click', () => this.testLLM());
        this.panel.querySelector('#s-clear-memory').addEventListener('click', () => this.clearMemory());
        this.panel.querySelector('#s-export-brain').addEventListener('click', () => this.exportBrain());

        // Sliders update labels
        this.panel.querySelector('#s-collect-interval').addEventListener('input', (e) => {
            this.panel.querySelector('#s-collect-interval-val').textContent = e.target.value + 's';
        });
        this.panel.querySelector('#s-screen-interval').addEventListener('input', (e) => {
            this.panel.querySelector('#s-screen-interval-val').textContent = e.target.value + 's';
        });
        this.panel.querySelector('#s-tts-speed').addEventListener('input', (e) => {
            this.panel.querySelector('#s-tts-speed-val').textContent = e.target.value + 'x';
        });
        this.panel.querySelector('#s-anim-speed').addEventListener('input', (e) => {
            this.panel.querySelector('#s-anim-speed-val').textContent = e.target.value + 'x';
        });
    }
};
