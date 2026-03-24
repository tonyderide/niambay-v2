/**
 * Niam-Bay 3D Hologram — Energy Sphere with Orbiting Particles
 *
 * Requires Three.js loaded before this file.
 * Usage:
 *   Hologram.init(document.getElementById('hologram-container'));
 *   Hologram.setState('thinking');
 */

const Hologram = {
    // Three.js core
    scene: null,
    camera: null,
    renderer: null,

    // Objects
    sphere: null,
    innerGlow: null,
    particles: null,
    rings: [],
    outerGlow: null,
    trailParticles: null,

    // State
    state: 'idle',
    _targetState: 'idle',
    _stateTransition: 1.0,
    _alertTimer: 0,
    _prevState: 'idle',

    // Animation clock
    _clock: null,
    _elapsed: 0,

    // Mouse tracking for particle trails
    _mouse: { x: 0, y: 0 },
    _mouseNorm: { x: 0, y: 0 },
    _mouseActive: false,
    _mouseTimeout: null,

    // Breathing / system load
    _systemLoad: 0.0,  // 0.0 to 1.0
    _breathPhase: 0,

    // Notification pulse
    _notifPulse: 0,
    _notifPulseDecay: 2.0,

    // State color targets
    _stateColors: {
        idle:      new THREE.Color(0x4a9eff),
        speaking:  new THREE.Color(0xddeeff),
        listening: new THREE.Color(0x9a4aff),
        thinking:  new THREE.Color(0x4affff),
        alert:     new THREE.Color(0xff4a4a),
    },

    // State parameters: pulseSpeed, pulseAmp, rotSpeed, particleOrbitSpeed, particleSpread, ringActive
    _stateParams: {
        idle:      { pulseSpeed: 0.17, pulseAmp: 0.05, rotSpeed: 0.05, orbitSpeed: 0.1,  spread: 0.0, ringActive: false },
        speaking:  { pulseSpeed: 0.72, pulseAmp: 0.08, rotSpeed: 0.15, orbitSpeed: 0.36, spread: 0.6, ringActive: false },
        listening: { pulseSpeed: 0.42, pulseAmp: 0.06, rotSpeed: 0.12, orbitSpeed: 0.24, spread: 0.0, ringActive: true  },
        thinking:  { pulseSpeed: 1.08, pulseAmp: 0.04, rotSpeed: 0.48, orbitSpeed: 0.9,  spread: 0.0, ringActive: false },
        alert:     { pulseSpeed: 1.8,  pulseAmp: 0.15, rotSpeed: 0.3,  orbitSpeed: 0.6,  spread: 0.2, ringActive: false },
    },

    // Current interpolated params
    _params: { pulseSpeed: 0.17, pulseAmp: 0.05, rotSpeed: 0.05, orbitSpeed: 0.1, spread: 0.0, ringActive: false },

    // Particle data
    _particleCount: 300,
    _particleBasePositions: null,
    _particleOrbitRadii: null,
    _particleOrbitSpeeds: null,
    _particlePhases: null,
    _particleInclinations: null,

    // Trail particle data
    _trailCount: 80,
    _trailPositions: null,
    _trailAlphas: null,
    _trailHead: 0,
    _trailLastUpdate: 0,

    // Ring data
    _ringCount: 4,

    init(container) {
        if (!container) {
            console.error('Hologram: container element required');
            return;
        }

        this._clock = new THREE.Clock();

        // --- Scene ---
        this.scene = new THREE.Scene();

        // --- Camera ---
        const w = container.clientWidth || 600;
        const h = container.clientHeight || 600;
        this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
        this.camera.position.set(0, 0, 6);
        this.camera.lookAt(0, 0, 0);

        // --- Renderer ---
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x000000, 0);
        container.appendChild(this.renderer.domElement);

        // --- Wireframe Sphere ---
        const sphereGeo = new THREE.IcosahedronGeometry(1.5, 3);
        const sphereMat = new THREE.MeshBasicMaterial({
            color: 0x4a9eff,
            wireframe: true,
            transparent: true,
            opacity: 0.6,
        });
        this.sphere = new THREE.Mesh(sphereGeo, sphereMat);
        this.scene.add(this.sphere);

        // --- Inner Glow Sphere ---
        const innerGeo = new THREE.IcosahedronGeometry(1.35, 4);
        const innerMat = new THREE.MeshBasicMaterial({
            color: 0x4a9eff,
            transparent: true,
            opacity: 0.08,
            side: THREE.BackSide,
        });
        this.innerGlow = new THREE.Mesh(innerGeo, innerMat);
        this.scene.add(this.innerGlow);

        // --- Outer Glow (large soft sphere) ---
        const outerGeo = new THREE.SphereGeometry(2.2, 32, 32);
        const outerMat = new THREE.MeshBasicMaterial({
            color: 0x4a9eff,
            transparent: true,
            opacity: 0.03,
            side: THREE.BackSide,
        });
        this.outerGlow = new THREE.Mesh(outerGeo, outerMat);
        this.scene.add(this.outerGlow);

        // --- Particles ---
        this._initParticles();

        // --- Trail Particles (mouse follow) ---
        this._initTrailParticles();

        // --- Rings (for listening state) ---
        this._initRings();

        // --- Lights ---
        const ambient = new THREE.AmbientLight(0xffffff, 0.3);
        this.scene.add(ambient);

        const pointLight = new THREE.PointLight(0x4a9eff, 2, 20);
        pointLight.position.set(0, 0, 0);
        this.scene.add(pointLight);
        this._pointLight = pointLight;

        // --- Resize handler ---
        this._container = container;
        this._onResize = () => this.resize();
        window.addEventListener('resize', this._onResize);

        // --- Mouse tracking ---
        this._onMouseMove = (e) => this._handleMouseMove(e);
        this._onMouseLeave = () => { this._mouseActive = false; };
        container.addEventListener('mousemove', this._onMouseMove);
        container.addEventListener('mouseleave', this._onMouseLeave);

        // --- Start ---
        this.animate();
    },

    _handleMouseMove(e) {
        const rect = this._container.getBoundingClientRect();
        // Normalized -1 to 1
        this._mouseNorm.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        this._mouseNorm.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        this._mouseActive = true;

        // Reset mouse timeout
        if (this._mouseTimeout) clearTimeout(this._mouseTimeout);
        this._mouseTimeout = setTimeout(() => { this._mouseActive = false; }, 2000);
    },

    _initParticles() {
        const count = this._particleCount;
        const positions = new Float32Array(count * 3);
        const alphas = new Float32Array(count);

        this._particleOrbitRadii = new Float32Array(count);
        this._particleOrbitSpeeds = new Float32Array(count);
        this._particlePhases = new Float32Array(count);
        this._particleInclinations = new Float32Array(count);
        this._particleBasePositions = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
            const r = 1.8 + Math.random() * 1.7;
            this._particleOrbitRadii[i] = r;
            this._particleOrbitSpeeds[i] = 0.5 + Math.random() * 1.0;
            this._particlePhases[i] = Math.random() * Math.PI * 2;
            this._particleInclinations[i] = (Math.random() - 0.5) * Math.PI;

            const theta = this._particlePhases[i];
            const incl = this._particleInclinations[i];
            positions[i * 3]     = r * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(theta) * Math.sin(incl);
            positions[i * 3 + 2] = r * Math.sin(theta) * Math.cos(incl);

            alphas[i] = 0.3 + Math.random() * 0.7;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const vertexShader = `
            attribute float alpha;
            varying float vAlpha;
            uniform float uSize;
            void main() {
                vAlpha = alpha;
                vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = uSize * (300.0 / -mvPosition.z);
                gl_Position = projectionMatrix * mvPosition;
            }
        `;

        const fragmentShader = `
            uniform vec3 uColor;
            varying float vAlpha;
            void main() {
                float d = length(gl_PointCoord - vec2(0.5));
                if (d > 0.5) discard;
                float glow = 1.0 - smoothstep(0.0, 0.5, d);
                glow = pow(glow, 1.5);
                gl_FragColor = vec4(uColor, glow * vAlpha);
            }
        `;

        const material = new THREE.ShaderMaterial({
            uniforms: {
                uColor: { value: new THREE.Color(0x4a9eff) },
                uSize:  { value: 0.08 },
            },
            vertexShader,
            fragmentShader,
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
        });

        geometry.setAttribute('alpha', new THREE.BufferAttribute(alphas, 1));

        this.particles = new THREE.Points(geometry, material);
        this.scene.add(this.particles);
    },

    _initTrailParticles() {
        const count = this._trailCount;
        const positions = new Float32Array(count * 3);
        const alphas = new Float32Array(count);

        // Initialize all trails off-screen
        for (let i = 0; i < count; i++) {
            positions[i * 3] = 0;
            positions[i * 3 + 1] = 0;
            positions[i * 3 + 2] = -100;
            alphas[i] = 0;
        }

        this._trailPositions = positions;
        this._trailAlphas = alphas;

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('alpha', new THREE.BufferAttribute(alphas, 1));

        const vertexShader = `
            attribute float alpha;
            varying float vAlpha;
            void main() {
                vAlpha = alpha;
                vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = max(2.0, 6.0 * alpha) * (300.0 / -mvPosition.z);
                gl_Position = projectionMatrix * mvPosition;
            }
        `;

        const fragmentShader = `
            uniform vec3 uColor;
            varying float vAlpha;
            void main() {
                float d = length(gl_PointCoord - vec2(0.5));
                if (d > 0.5) discard;
                float glow = 1.0 - smoothstep(0.0, 0.5, d);
                glow = pow(glow, 2.0);
                gl_FragColor = vec4(uColor, glow * vAlpha * 0.7);
            }
        `;

        const material = new THREE.ShaderMaterial({
            uniforms: {
                uColor: { value: new THREE.Color(0x4fc3f7) },
            },
            vertexShader,
            fragmentShader,
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
        });

        this.trailParticles = new THREE.Points(geometry, material);
        this.scene.add(this.trailParticles);
    },

    _initRings() {
        this.rings = [];
        for (let i = 0; i < this._ringCount; i++) {
            const ringGeo = new THREE.RingGeometry(1.6, 1.65, 64);
            const ringMat = new THREE.MeshBasicMaterial({
                color: 0x9a4aff,
                transparent: true,
                opacity: 0.0,
                side: THREE.DoubleSide,
            });
            const ring = new THREE.Mesh(ringGeo, ringMat);
            ring.userData = {
                phase: (i / this._ringCount) * Math.PI * 2,
                scale: 1.0,
                opacity: 0.0,
                active: false,
            };
            this.scene.add(ring);
            this.rings.push(ring);
        }
    },

    setState(newState) {
        if (!this._stateParams[newState]) {
            console.warn('Hologram: unknown state "' + newState + '"');
            return;
        }

        if (newState === 'alert') {
            this._alertTimer = 0.6;
            this._prevState = this.state === 'alert' ? this._prevState : this.state;
            this._targetState = 'alert';
        } else {
            this._targetState = newState;
            this._prevState = newState;
        }

        this.state = newState;
    },

    /**
     * Set system load (0.0 to 1.0) — affects breathing depth and speed.
     */
    setSystemLoad(load) {
        this._systemLoad = Math.max(0, Math.min(1, load));
    },

    /**
     * Trigger a notification pulse — the hologram briefly flashes brighter.
     */
    notificationPulse() {
        this._notifPulse = 1.0;
    },

    _lerpParam(current, target, speed) {
        return current + (target - current) * Math.min(1.0, speed);
    },

    animate() {
        requestAnimationFrame(() => this.animate());

        const delta = this._clock.getDelta();
        // Clamp delta to avoid huge jumps when tab is backgrounded
        const clampedDelta = Math.min(delta, 0.1);
        this._elapsed += clampedDelta;
        const time = this._elapsed;

        // --- Alert timer ---
        if (this._alertTimer > 0) {
            this._alertTimer -= clampedDelta;
            if (this._alertTimer <= 0) {
                this._alertTimer = 0;
                this._targetState = this._prevState;
                this.state = this._prevState;
            }
        }

        // --- Notification pulse decay ---
        if (this._notifPulse > 0) {
            this._notifPulse = Math.max(0, this._notifPulse - clampedDelta * this._notifPulseDecay);
        }

        // --- Interpolate parameters toward target state (smoother with cubic easing) ---
        const target = this._stateParams[this._targetState];
        const lerpSpeed = clampedDelta * 3.0;
        this._params.pulseSpeed  = this._lerpParam(this._params.pulseSpeed,  target.pulseSpeed,  lerpSpeed);
        this._params.pulseAmp    = this._lerpParam(this._params.pulseAmp,    target.pulseAmp,    lerpSpeed);
        this._params.rotSpeed    = this._lerpParam(this._params.rotSpeed,    target.rotSpeed,    lerpSpeed);
        this._params.orbitSpeed  = this._lerpParam(this._params.orbitSpeed,  target.orbitSpeed,  lerpSpeed);
        this._params.spread      = this._lerpParam(this._params.spread,      target.spread,      lerpSpeed);

        // --- Breathing varies with system load ---
        // Higher load = faster, deeper breathing
        const loadBreathMul = 1.0 + this._systemLoad * 0.8;
        const loadAmpMul = 1.0 + this._systemLoad * 0.5;
        const effectivePulseSpeed = this._params.pulseSpeed * loadBreathMul;
        const effectivePulseAmp = this._params.pulseAmp * loadAmpMul;

        // --- Color interpolation (smoother) ---
        const targetColor = this._stateColors[this._targetState];
        const colorSpeed = lerpSpeed * 2;
        this.sphere.material.color.lerp(targetColor, colorSpeed);
        this.innerGlow.material.color.lerp(targetColor, colorSpeed);
        this.outerGlow.material.color.lerp(targetColor, colorSpeed);
        this._pointLight.color.lerp(targetColor, colorSpeed);
        this.particles.material.uniforms.uColor.value.lerp(targetColor, colorSpeed);

        // --- Sphere rotation (smoother via accumulated angle) ---
        this.sphere.rotation.x += this._params.rotSpeed * clampedDelta;
        this.sphere.rotation.y += this._params.rotSpeed * clampedDelta * 1.3;
        this.innerGlow.rotation.x = this.sphere.rotation.x * 0.5;
        this.innerGlow.rotation.y = this.sphere.rotation.y * 0.5;

        // --- Sphere breathing pulse with load influence ---
        this._breathPhase += clampedDelta * effectivePulseSpeed * Math.PI * 2;
        const breathSin = Math.sin(this._breathPhase);
        // Add a subtle second harmonic for organic feel
        const breathSin2 = Math.sin(this._breathPhase * 0.37) * 0.3;
        const pulse = 1.0 + (breathSin + breathSin2) * effectivePulseAmp;

        // Add notification pulse effect
        const notifScale = 1.0 + this._notifPulse * 0.15;

        this.sphere.scale.setScalar(pulse * notifScale);
        this.innerGlow.scale.setScalar(pulse * 0.95 * notifScale);
        this.outerGlow.scale.setScalar(pulse * 1.1 * notifScale);

        // --- Inner glow opacity pulse (varies with load) ---
        const baseInnerOpacity = 0.06 + this._systemLoad * 0.04;
        this.innerGlow.material.opacity = baseInnerOpacity + Math.sin(time * 0.5) * 0.03;
        this.outerGlow.material.opacity = 0.02 + Math.sin(time * 0.25) * 0.015 + this._notifPulse * 0.06;

        // --- Wireframe opacity shimmer ---
        this.sphere.material.opacity = 0.5 + Math.sin(time * 0.7) * 0.15 + this._notifPulse * 0.2;

        // --- Point light intensity (notification pulse makes it brighter) ---
        const baseLightIntensity = this._targetState === 'speaking' ? 3.5 : 2.0;
        this._pointLight.intensity = baseLightIntensity + Math.sin(time * 1.0) * 0.5 + this._notifPulse * 3.0;

        // --- Particle orbits ---
        this._updateParticles(time, clampedDelta);

        // --- Trail particles (mouse follow) ---
        this._updateTrailParticles(time, clampedDelta);

        // --- Rings (listening wave) ---
        this._updateRings(time, clampedDelta);

        // --- Render ---
        this.renderer.render(this.scene, this.camera);
    },

    _updateParticles(time, delta) {
        const positions = this.particles.geometry.attributes.position.array;
        const alphas = this.particles.geometry.attributes.alpha.array;
        const count = this._particleCount;
        const orbitSpeed = this._params.orbitSpeed;
        const spread = this._params.spread;

        // Mouse attraction: particles near the mouse get gently pulled
        const mouseInfluence = this._mouseActive ? 0.3 : 0;

        for (let i = 0; i < count; i++) {
            const r = this._particleOrbitRadii[i] + spread;
            const speed = this._particleOrbitSpeeds[i] * orbitSpeed;
            const phase = this._particlePhases[i];
            const incl = this._particleInclinations[i];

            const theta = phase + time * speed;

            const x = r * Math.cos(theta);
            const yFlat = r * Math.sin(theta);

            let px = x * Math.cos(incl);
            let py = yFlat;
            let pz = x * Math.sin(incl);

            // Gentle vertical wobble
            py += Math.sin(time * 0.5 + phase) * 0.15;

            // Mouse attraction (gentle pull toward mouse in world coords)
            if (mouseInfluence > 0) {
                const mx = this._mouseNorm.x * 3.5;
                const my = this._mouseNorm.y * 3.5;
                const dx = mx - px;
                const dy = my - py;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 3.0) {
                    const strength = mouseInfluence * (1.0 - dist / 3.0) * delta * 2;
                    px += dx * strength;
                    py += dy * strength;
                }
            }

            positions[i * 3]     = px;
            positions[i * 3 + 1] = py;
            positions[i * 3 + 2] = pz;

            // Notification pulse: all particles briefly flash
            if (this._notifPulse > 0) {
                alphas[i] = Math.min(1.0, (0.3 + Math.random() * 0.7) + this._notifPulse * 0.5);
            }
        }

        this.particles.geometry.attributes.position.needsUpdate = true;
        if (this._notifPulse > 0) {
            this.particles.geometry.attributes.alpha.needsUpdate = true;
        }
    },

    _updateTrailParticles(time, delta) {
        if (!this._mouseActive) {
            // Fade all trails out
            let anyVisible = false;
            for (let i = 0; i < this._trailCount; i++) {
                if (this._trailAlphas[i] > 0) {
                    this._trailAlphas[i] = Math.max(0, this._trailAlphas[i] - delta * 1.5);
                    anyVisible = true;
                }
            }
            if (anyVisible) {
                this.trailParticles.geometry.attributes.alpha.needsUpdate = true;
            }
            return;
        }

        // Add new trail point every ~20ms
        this._trailLastUpdate += delta;
        if (this._trailLastUpdate > 0.02) {
            this._trailLastUpdate = 0;

            const idx = this._trailHead;
            // Convert mouse normalized coords to world-ish coords
            const wx = this._mouseNorm.x * 3.5;
            const wy = this._mouseNorm.y * 3.5;

            // Add slight randomness for sparkle
            this._trailPositions[idx * 3]     = wx + (Math.random() - 0.5) * 0.3;
            this._trailPositions[idx * 3 + 1] = wy + (Math.random() - 0.5) * 0.3;
            this._trailPositions[idx * 3 + 2] = (Math.random() - 0.5) * 0.5;
            this._trailAlphas[idx] = 1.0;

            this._trailHead = (this._trailHead + 1) % this._trailCount;
        }

        // Decay all trail alphas
        for (let i = 0; i < this._trailCount; i++) {
            if (this._trailAlphas[i] > 0) {
                this._trailAlphas[i] = Math.max(0, this._trailAlphas[i] - delta * 1.2);
            }
        }

        this.trailParticles.geometry.attributes.position.needsUpdate = true;
        this.trailParticles.geometry.attributes.alpha.needsUpdate = true;
    },

    _updateRings(time, delta) {
        const isListening = this._targetState === 'listening';

        for (let i = 0; i < this.rings.length; i++) {
            const ring = this.rings[i];

            if (isListening) {
                const cycleTime = 2.5;
                const phase = (time + (i / this.rings.length) * cycleTime) % cycleTime;
                const progress = phase / cycleTime;

                const scale = 1.0 + progress * 2.5;
                const opacity = Math.sin(progress * Math.PI) * 0.4;

                ring.scale.setScalar(scale);
                ring.material.opacity = opacity;
                ring.material.color.lerp(this._stateColors.listening, delta * 5);

                ring.rotation.x = Math.PI * 0.5 + Math.sin(time * 0.3 + i) * 0.15;
                ring.rotation.z = Math.sin(time * 0.2 + i * 0.5) * 0.1;
            } else {
                ring.material.opacity = Math.max(0, ring.material.opacity - delta * 2);
                if (ring.material.opacity <= 0) {
                    ring.scale.setScalar(1.0);
                }
            }
        }
    },

    resize() {
        if (!this._container || !this.renderer || !this.camera) return;
        const w = this._container.clientWidth;
        const h = this._container.clientHeight;
        if (w === 0 || h === 0) return;

        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
    },

    /**
     * Clean up resources. Call when removing the hologram.
     */
    destroy() {
        window.removeEventListener('resize', this._onResize);
        if (this._container) {
            this._container.removeEventListener('mousemove', this._onMouseMove);
            this._container.removeEventListener('mouseleave', this._onMouseLeave);
        }

        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }

        if (this.scene) {
            this.scene.traverse((obj) => {
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) {
                    if (Array.isArray(obj.material)) {
                        obj.material.forEach(m => m.dispose());
                    } else {
                        obj.material.dispose();
                    }
                }
            });
        }

        this.scene = null;
        this.camera = null;
        this.renderer = null;
    }
};
