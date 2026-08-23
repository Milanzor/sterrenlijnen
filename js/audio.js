// Procedurele audio met WebAudio: geen bestanden, alles gesynthetiseerd.
// Stipjes lopen een pentatonische ladder op; bij duo-figuren klinkt de tweede
// hand een terts hoger — samen spelen klinkt dan letterlijk als samenspel.

const PENTA = [261.63, 293.66, 329.63, 392.00, 440.00,
               523.25, 587.33, 659.26, 784.00, 880.00];
const MAJOR = [0, 2, 4, 5, 7, 9, 11];
const degFreq = (deg, oct = 0) =>
  440 * 2 ** ((60 + 12 * (oct + Math.floor(deg / 7)) + MAJOR[((deg % 7) + 7) % 7] - 69) / 12);

export class Geluid {
  constructor() {
    this.ctx = null;
    this.aan = true;
    this._ladder = 0;
    this._lastPop = -10;
    this._muziekTimer = null;
  }

  init() {  // pas na een klik/tik (autoplay-regels)
    if (this.ctx) return;
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.master = this.ctx.createGain();
    this.master.gain.value = 1.0;
    this.master.connect(this.ctx.destination);
    this.muziekBus = this.ctx.createGain();
    this.muziekBus.gain.value = 0.16;
    this.muziekBus.connect(this.master);
    this._startMuziek();
  }

  zetAan(aan) {
    this.aan = aan;
    if (this.master) {
      this.master.gain.setTargetAtTime(aan ? 1.0 : 0.0, this.ctx.currentTime, 0.05);
    }
  }

  _toon(freq, dur, { at = 0, gain = 0.5, type = "sine", bus = this.master,
                     attack = 0.005, harm = 0.4 } = {}) {
    const t0 = this.ctx.currentTime + at;
    const g = this.ctx.createGain();
    g.connect(bus);
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(gain, t0 + attack);
    g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    for (const [mul, amp, tp] of [[1, 1, type], [2, harm, "sine"], [3, harm * 0.4, "sine"]]) {
      const o = this.ctx.createOscillator();
      o.type = tp;
      o.frequency.value = freq * mul;
      const og = this.ctx.createGain();
      og.gain.value = amp / (1 + harm * 1.4);
      o.connect(og).connect(g);
      o.start(t0);
      o.stop(t0 + dur + 0.05);
    }
  }

  _ruis(dur, { at = 0, gain = 0.2, dof = 24 } = {}) {
    const t0 = this.ctx.currentTime + at;
    const n = Math.floor(this.ctx.sampleRate * dur);
    const buf = this.ctx.createBuffer(1, n, this.ctx.sampleRate);
    const d = buf.getChannelData(0);
    let acc = 0;
    for (let i = 0; i < n; i++) {  // dofgemaakte ruis (lopende middeling)
      acc += (Math.random() * 2 - 1 - acc) / dof;
      d[i] = acc * dof * 0.35 * (1 - i / n) ** 2;
    }
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    const g = this.ctx.createGain();
    g.gain.value = gain;
    src.connect(g).connect(this.master);
    src.start(t0);
  }

  // ---------- effecten ----------

  pop(duoTerts = false) {
    if (!this.ctx) return;
    const now = this.ctx.currentTime;
    if (now - this._lastPop > 1.5) this._ladder = 0;
    this._lastPop = now;
    const i = this._ladder % PENTA.length;
    this._ladder++;
    this._toon(PENTA[i], 0.42, { gain: 0.4 });
    if (duoTerts) this._toon(PENTA[(i + 2) % PENTA.length], 0.42, { gain: 0.28 });
  }

  tada() {
    if (!this.ctx) return;
    [[659.26, 0], [987.77, 0.13]].forEach(([f, at], i) =>
      this._toon(f, 0.55, { at, gain: i ? 0.42 : 0.32 }));
  }

  fanfare() {
    if (!this.ctx) return;
    [[392, 0], [523.25, 0.14], [784, 0.28]].forEach(([f, at], i) =>
      this._toon(f, 0.8, { at, gain: i === 2 ? 0.45 : 0.35 }));
  }

  glinster() {  // figuurtje af: snelle arpeggio omhoog
    if (!this.ctx) return;
    [523.25, 659.26, 784, 1046.5, 1318.5].forEach((f, i) =>
      this._toon(f, 0.45, { at: i * 0.07, gain: 0.26 }));
  }

  fizzle() {
    if (!this.ctx) return;
    this._ruis(0.3, { gain: 0.18 });
  }

  wacht() {  // duo: de ene hand wacht op de andere — vriendelijk tikje
    if (!this.ctx) return;
    this._toon(392, 0.12, { gain: 0.12 });
  }

  zeg(tekst) {  // Letter leer modus: spreek de letter uit (Nederlands)
    if (!this.aan || typeof speechSynthesis === "undefined") return;
    try {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(tekst);
      u.lang = "nl-NL";
      u.rate = 0.8;
      u.pitch = 1.1;
      speechSynthesis.speak(u);
    } catch { /* geen stem beschikbaar: dan alleen de nootjes */ }
  }

  // ---------- muziekje ----------
  // Eén vrolijk loopje (tokkelmelodie + bas), gepland met een lookahead-timer.

  _startMuziek() {
    const bpm = 112, spb = 60 / bpm;
    // maten van 4 tellen; akkoorden I–vi–IV–V; melodie als [tel, duur, graad]
    const chords = [0, 5, 3, 4];
    const melA = [[0, 1, 0], [1, 1, 1], [2, 1, 2], [3, 1, 1]];
    const melB = [[0, 1, 2], [1, 1, 3], [2, 2, 2]];
    const steps = [0, 2, 4, 7, 9];
    const barLen = 4 * spb, loopLen = chords.length * barLen;
    let nextLoop = this.ctx.currentTime + 0.1;
    const plan = () => {
      if (!this.ctx) return;
      while (nextLoop < this.ctx.currentTime + 1.2) {
        const at0 = nextLoop - this.ctx.currentTime;
        chords.forEach((root, bar) => {
          const mel = bar % 2 === 0 ? melA : melB;
          for (const [beat, dur, step] of mel) {
            this._toon(degFreq(root + steps[step % steps.length], 1), dur * spb * 0.9,
                       { at: at0 + bar * barLen + beat * spb, gain: 0.5,
                         bus: this.muziekBus, harm: 0.5 });
          }
          this._toon(degFreq(root, -1), 0.9 * spb,
                     { at: at0 + bar * barLen, gain: 0.5, bus: this.muziekBus });
          this._toon(degFreq(root + 4, -1), 0.45 * spb,
                     { at: at0 + bar * barLen + 2 * spb, gain: 0.3, bus: this.muziekBus });
        });
        nextLoop += loopLen;
      }
    };
    plan();
    this._muziekTimer = setInterval(plan, 400);
  }
}
