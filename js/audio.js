// Procedurele audio met WebAudio: geen bestanden, alles gesynthetiseerd.
// Elke stip speelt de vólgende noot van een echt kinderliedje (alleen de
// toonhoogtes — het ritme bepaal je zelf met je vinger). Bij duo-figuren
// klinkt de tweede hand een terts hoger.

const MAJOR = [0, 2, 4, 5, 7, 9, 11];
const degFreq = (deg, oct = 0) =>
  440 * 2 ** ((60 + 12 * (oct + Math.floor(deg / 7)) + MAJOR[((deg % 7) + 7) % 7] - 69) / 12);

// Liedjesbank: melodieën als toonladder-graden in majeur (0 = do, negatief =
// onder de do). Een lied loopt gewoon door over stippen, halen en levels heen;
// is het uit, dan komt het volgende van de geschudde stapel — pas als álle
// liedjes geweest zijn wordt er opnieuw geschud, dus niks herhaalt snel.
const LIEDJES = [
  // Vader Jacob
  [0, 1, 2, 0, 0, 1, 2, 0, 2, 3, 4, 2, 3, 4,
   4, 5, 4, 3, 2, 0, 4, 5, 4, 3, 2, 0, 0, -3, 0, 0, -3, 0],
  // Altijd is Kortjakje ziek
  [0, 0, 4, 4, 5, 5, 4, 3, 3, 2, 2, 1, 1, 0,
   4, 4, 3, 3, 2, 2, 1, 4, 4, 3, 3, 2, 2, 1,
   0, 0, 4, 4, 5, 5, 4, 3, 3, 2, 2, 1, 1, 0],
  // Poesje mauw
  [4, 2, 2, 3, 1, 1, 0, 1, 2, 3, 4, 4, 4,
   4, 2, 2, 3, 1, 1, 0, 2, 4, 4, 0],
  // Mary had a little lamb
  [2, 1, 0, 1, 2, 2, 2, 1, 1, 1, 2, 4, 4,
   2, 1, 0, 1, 2, 2, 2, 2, 1, 1, 2, 1, 0],
  // Ode an die Freude (Beethoven)
  [2, 2, 3, 4, 4, 3, 2, 1, 0, 0, 1, 2, 2, 1, 1,
   2, 2, 3, 4, 4, 3, 2, 1, 0, 0, 1, 2, 1, 0, 0],
  // London Bridge
  [4, 5, 4, 3, 2, 3, 4, 1, 2, 3, 2, 3, 4,
   4, 5, 4, 3, 2, 3, 4, 1, 4, 2, 0],
  // Row, row, row your boat
  [0, 0, 0, 1, 2, 2, 1, 2, 3, 4,
   7, 7, 7, 4, 4, 4, 2, 2, 2, 0, 0, 0, 4, 3, 2, 1, 0],
  // Lang zal die leven (Happy Birthday)
  [-3, -3, -2, -3, 0, -1, -3, -3, -2, -3, 1, 0,
   -3, -3, 4, 2, 0, -1, -2, 3, 3, 2, 0, 1, 0],
  // Jingle Bells (refrein)
  [2, 2, 2, 2, 2, 2, 2, 4, 0, 1, 2,
   3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 2, 1, 4,
   2, 2, 2, 2, 2, 2, 2, 4, 0, 1, 2,
   3, 3, 3, 3, 3, 2, 2, 2, 4, 4, 3, 1, 0],
  // Old MacDonald
  [0, 0, 0, -3, -2, -2, -3, 2, 2, 1, 1, 0,
   -3, 0, 0, 0, -3, -2, -2, -3, 2, 2, 1, 1, 0],
  // When the Saints Go Marching In
  [0, 2, 3, 4, 0, 2, 3, 4, 0, 2, 3, 4, 2, 0, 2, 1,
   2, 2, 1, 0, 0, 2, 4, 4, 4, 3, 2, 3, 4, 2, 0, 1, 0],
  // Au clair de la lune
  [0, 0, 0, 1, 2, 1, 0, 2, 1, 1, 0,
   0, 0, 0, 1, 2, 1, 0, 2, 1, 1, 0],
  // Hot Cross Buns
  [2, 1, 0, 2, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 1, 0],
  // Hansje Pansje Kevertje (Itsy Bitsy Spider)
  [-3, 0, 0, 0, 1, 2, 2, 2, 1, 0, 1, 2, 0,
   2, 2, 3, 4, 4, 3, 2, 3, 4, 2,
   0, 0, 1, 2, 2, 1, 0, 1, 2, 0,
   -3, -3, 0, 0, 0, 1, 2, 2, 2, 1, 0, 1, 2, 0],
  // This Old Man
  [4, 2, 4, 4, 2, 4, 5, 4, 3, 2, 1, 2, 3,
   2, 3, 4, 0, 0, 0, 0, 0, 1, 2, 3, 4, 4, 1, 1, 3, 2, 1, 0],
  // Yankee Doodle
  [0, 0, 1, 2, 0, 2, 1, -3, 0, 0, 1, 2, 0, -1,
   0, 0, 1, 2, 3, 2, 1, 0, -1, -3, -2, -1, 0, 0],
  // Camptown Races
  [4, 4, 2, 4, 5, 4, 2, 2, 1, 2, 1,
   4, 4, 2, 4, 5, 4, 2, 1, 2, 1, 0],
  // Oh! Susanna
  [0, 1, 2, 4, 4, 5, 4, 2, 0, 1, 2, 2, 1, 0, 1,
   0, 1, 2, 4, 4, 5, 4, 2, 0, 1, 2, 2, 1, 1, 0],
];

const GELUID_OPSLAG = "sterrenlijnen-geluid";

export class Geluid {
  constructor() {
    this.ctx = null;
    this.aan = true;
    try { this.aan = localStorage.getItem(GELUID_OPSLAG) !== "uit"; } catch { /* privémodus */ }
    this._lied = null;    // huidige melodie (graden)
    this._noot = 0;       // positie in de melodie
    this._stapel = [];    // geschudde stapel liedjes die nog moeten
    this._vorigLied = -1;
    this._muziekTimer = null;
  }

  init() {  // pas na een klik/tik (autoplay-regels)
    if (this.ctx) return;
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.master = this.ctx.createGain();
    this.master.gain.value = this.aan ? 1.0 : 0.0;
    // begrenzer: tada + arpeggio + nootje tegelijk mag niet kraken
    const rem = this.ctx.createDynamicsCompressor();
    rem.threshold.value = -10;
    rem.ratio.value = 12;
    rem.attack.value = 0.003;
    rem.release.value = 0.2;
    this.master.connect(rem).connect(this.ctx.destination);
    this.muziekBus = this.ctx.createGain();
    this.muziekBus.gain.value = 0.16;
    this.muziekBus.connect(this.master);
    this._startMuziek();
  }

  zetAan(aan) {
    this.aan = aan;
    try { localStorage.setItem(GELUID_OPSLAG, aan ? "aan" : "uit"); } catch { /* privémodus */ }
    if (!aan && typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
    if (this.master) {
      this.master.gain.setTargetAtTime(aan ? 1.0 : 0.0, this.ctx.currentTime, 0.05);
    }
  }

  pauzeer(ja) {  // tabblad uit beeld: geen muziek op de achtergrond
    if (!this.ctx) return;
    if (ja) {
      this.ctx.suspend();
      if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
    } else {
      this.ctx.resume();
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

  _volgendeNoot() {
    if (!this._lied || this._noot >= this._lied.length) {
      if (!this._stapel.length) {  // alles gehad: opnieuw schudden (Fisher-Yates)
        this._stapel = LIEDJES.map((_, i) => i);
        for (let i = this._stapel.length - 1; i > 0; i--) {
          const j = (Math.random() * (i + 1)) | 0;
          [this._stapel[i], this._stapel[j]] = [this._stapel[j], this._stapel[i]];
        }
        // niet hetzelfde lied twee keer achter elkaar
        if (this._stapel[this._stapel.length - 1] === this._vorigLied) {
          this._stapel.unshift(this._stapel.pop());
        }
      }
      this._vorigLied = this._stapel.pop();
      this._lied = LIEDJES[this._vorigLied];
      this._noot = 0;
    }
    return this._lied[this._noot++];
  }

  pop(duoTerts = false) {
    if (!this.ctx) return;
    const noot = this._volgendeNoot();
    this._toon(degFreq(noot), 0.42, { gain: 0.4 });
    if (duoTerts) this._toon(degFreq(noot + 2), 0.42, { gain: 0.28 });
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
      // Kies zelf een Nederlandse stem: alleen `lang` zetten laat sommige
      // browsers een Engelse stem Nederlands voorlezen — dan liever stil.
      const stemmen = speechSynthesis.getVoices();
      const nl = stemmen.find(v => v.lang.replace("_", "-") === "nl-NL")
              ?? stemmen.find(v => /^nl\b/i.test(v.lang));
      if (stemmen.length && !nl) return;
      const u = new SpeechSynthesisUtterance(tekst);
      if (nl) u.voice = nl;
      u.lang = "nl-NL";
      u.rate = 0.8;
      u.pitch = 1.1;
      speechSynthesis.speak(u);
    } catch { /* geen stem beschikbaar: dan alleen de nootjes */ }
  }

  // ---------- muziekje ----------
  // Zachte bas/akkoord-puls (I–vi–IV–V), gepland met een lookahead-timer.
  // Bewust géén eigen melodielijn: de mélodie komt van de stipjes — dat zijn
  // echte kinderliedjes, en die moeten herkenbaar blijven.

  _startMuziek() {
    const bpm = 112, spb = 60 / bpm;
    const chords = [0, 5, 3, 4];  // maten van 4 tellen; akkoorden I–vi–IV–V
    const barLen = 4 * spb, loopLen = chords.length * barLen;
    let nextLoop = this.ctx.currentTime + 0.1;
    const plan = () => {
      if (!this.ctx) return;
      while (nextLoop < this.ctx.currentTime + 1.2) {
        const at0 = nextLoop - this.ctx.currentTime;
        chords.forEach((root, bar) => {
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
