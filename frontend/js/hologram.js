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

    // State
    state: 'idle',
    _targetState: 'idle',
    _stateTransition: 1.0,
    _alertTimer: 0,
    _prevState: 'idle',

    // Animation clock
    _clock: null,
    _elapsed: 0,

    // State color targets
    _stateColors: {
        idle:      new THREE.Color(0x4a9eff),
        speaking:  new THREE.Color(0xddeeff),
        listening: new THREE.Color(0x9a4aff),
        thinking:  new THREE.Color(0x4affff),
        alert:     new THREE.Color(0xff4a4a),
    },

    // State parameters: [pulseSpeed, pulseAmp, rotSpeed, particleOrbitSpeed, particleSpread, ringActive]
    _stateParams: {
        idle:      { pulseSpeed: 0.5,  pulseAmp: 0.05, rotSpeed: 0.15, orbitSpeed: 0.3, spread: 0.0, ringActive: false },
        speaking:  { pulseSpeed: 1.2,  pulseAmp: 0.08, rotSpeed: 0.25, orbitSpeed: 0.6, spread: 0.6, ringActive: false },
        listening: { pulseSpeed: 0.7,  pulseAmp: 0.06, rotSpeed: 0.2,  orbitSpeed: 0.4, spread: 0.0, ringActive: true  },
        thinking:  { pulseSpeed: 1.8,  pulseAmp: 0.04, rotSpeed: 0.8,  orbitSpeed: 1.5, spread: 0.0, ringActive: false },
        alert:     { pulseSpeed: 3.0,  pulseAmp: 0.15, rotSpeed: 0.5,  orbitSpeed: 1.0, spread: 0.2, ringActive: false },
    },

    // Current interpolated params
    _params: { pulseSpeed: 0.5, pulseAmp: 0.05, rotSpeed: 0.15, orbitSpeed: 0.3, spread: 0.0, ringActive: false },

    // Particle data
    _particleCount: 300,
    _particleBasePositions: null,
    _particleOrbitRadii: null,
    _particleOrbitSpeeds: null,
    _particlePhases: null,
    _particleInclinations: null,

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

        // --- Start ---
        this.animate();
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
            // Orbit radius between 1.8 and 3.5
            const r = 1.8 + Math.random() * 1.7;
            this._particleOrbitRadii[i] = r;

            // Orbit speed variation
            this._particleOrbitSpeeds[i] = 0.5 + Math.random() * 1.0;

            // Random phase offset
            this._particlePhases[i] = Math.random() * Math.PI * 2;

            // Inclination (tilt of orbit plane)
            this._particleInclinations[i] = (Math.random() - 0.5) * Math.PI;

            // Initial position
            const theta = this._particlePhases[i];
            const incl = this._particleInclinations[i];
            positions[i * 3]     = r * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(theta) * Math.sin(incl);
            positions[i * 3 + 2] = r * Math.sin(theta) * Math.cos(incl);

            alphas[i] = 0.3 + Math.random() * 0.7;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        // Custom shader for particles with glow
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
            this._alertTimer = 0.6; // flash duration in seconds
            this._prevState = this.state === 'alert' ? this._prevState : this.state;
            this._targetState = 'alert';
        } else {
            this._targetState = newState;
            this._prevState = newState;
        }

        this.state = newState;
    },

    _lerpParam(current, target, speed) {
        return current + (target - current) * Math.min(1.0, speed);
    },

    animate() {
        requestAnimationFrame(() => this.animate());

        const delta = this._clock.getDelta();
        this._elapsed += delta;
        const time = this._elapsed;

        // --- Alert timer ---
        if (this._alertTimer > 0) {
            this._alertTimer -= delta;
            if (this._alertTimer <= 0) {
                this._alertTimer = 0;
                this._targetState = this._prevState;
                this.state = this._prevState;
            }
        }

        // --- Interpolate parameters toward target state ---
        const target = this._stateParams[this._targetState];
        const lerpSpeed = delta * 3.0;
        this._params.pulseSpeed  = this._lerpParam(this._params.pulseSpeed,  target.pulseSpeed,  lerpSpeed);
        this._params.pulseAmp    = this._lerpParam(this._params.pulseAmp,    target.pulseAmp,    lerpSpeed);
        this._params.rotSpeed    = this._lerpParam(this._params.rotSpeed,    target.rotSpeed,    lerpSpeed);
        this._params.orbitSpeed  = this._lerpParam(this._params.orbitSpeed,  target.orbitSpeed,  lerpSpeed);
        this._params.spread      = this._lerpParam(this._params.spread,      target.spread,      lerpSpeed);

        // --- Color interpolation ---
        const targetColor = this._stateColors[this._targetState];
        this.sphere.material.color.lerp(targetColor, lerpSpeed * 2);
        this.innerGlow.material.color.lerp(targetColor, lerpSpeed * 2);
        this.outerGlow.material.color.lerp(targetColor, lerpSpeed * 2);
        this._pointLight.color.lerp(targetColor, lerpSpeed * 2);
        this.particles.material.uniforms.uColor.value.lerp(targetColor, lerpSpeed * 2);

        // --- Sphere rotation ---
        this.sphere.rotation.x += this._params.rotSpeed * delta;
        this.sphere.rotation.y += this._params.rotSpeed * delta * 1.3;
        this.innerGlow.rotation.x = this.sphere.rotation.x * 0.5;
        this.innerGlow.rotation.y = this.sphere.rotation.y * 0.5;

        // --- Sphere breathing pulse ---
        const pulse = 1.0 + Math.sin(time * this._params.pulseSpeed * Math.PI * 2) * this._params.pulseAmp;
        this.sphere.scale.setScalar(pulse);
        this.innerGlow.scale.setScalar(pulse * 0.95);
        this.outerGlow.scale.setScalar(pulse * 1.1);

        // --- Inner glow opacity pulse ---
        this.innerGlow.material.opacity = 0.06 + Math.sin(time * 1.5) * 0.03;
        this.outerGlow.material.opacity = 0.02 + Math.sin(time * 0.8) * 0.015;

        // --- Wireframe opacity shimmer ---
        this.sphere.material.opacity = 0.5 + Math.sin(time * 2.0) * 0.15;

        // --- Point light intensity ---
        const baseLightIntensity = this._targetState === 'speaking' ? 3.5 : 2.0;
        this._pointLight.intensity = baseLightIntensity + Math.sin(time * 3.0) * 0.5;

        // --- Particle orbits ---
        this._updateParticles(time);

        // --- Rings (listening wave) ---
        this._updateRings(time, delta);

        // --- Render ---
        this.renderer.render(this.scene, this.camera);
    },

    _updateParticles(time) {
        const positions = this.particles.geometry.attributes.position.array;
        const count = this._particleCount;
        const orbitSpeed = this._params.orbitSpeed;
        const spread = this._params.spread;

        for (let i = 0; i < count; i++) {
            const r = this._particleOrbitRadii[i] + spread;
            const speed = this._particleOrbitSpeeds[i] * orbitSpeed;
            const phase = this._particlePhases[i];
            const incl = this._particleInclinations[i];

            const theta = phase + time * speed;

            // Orbit in a tilted plane
            const x = r * Math.cos(theta);
            const yFlat = r * Math.sin(theta);

            positions[i * 3]     = x * Math.cos(incl);
            positions[i * 3 + 1] = yFlat;
            positions[i * 3 + 2] = x * Math.sin(incl);

            // Add a gentle vertical wobble
            positions[i * 3 + 1] += Math.sin(time * 0.5 + phase) * 0.15;
        }

        this.particles.geometry.attributes.position.needsUpdate = true;
    },

    _updateRings(time, delta) {
        const isListening = this._targetState === 'listening';

        for (let i = 0; i < this.rings.length; i++) {
            const ring = this.rings[i];
            const ud = ring.userData;

            if (isListening) {
                // Animate ring expansion
                const cycleTime = 2.5; // seconds per full wave cycle
                const phase = (time + (i / this.rings.length) * cycleTime) % cycleTime;
                const progress = phase / cycleTime;

                const scale = 1.0 + progress * 2.5;
                const opacity = Math.sin(progress * Math.PI) * 0.4;

                ring.scale.setScalar(scale);
                ring.material.opacity = opacity;
                ring.material.color.lerp(this._stateColors.listening, delta * 5);

                // Slight tilt for each ring for depth
                ring.rotation.x = Math.PI * 0.5 + Math.sin(time * 0.3 + i) * 0.15;
                ring.rotation.z = Math.sin(time * 0.2 + i * 0.5) * 0.1;
            } else {
                // Fade rings out smoothly
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
