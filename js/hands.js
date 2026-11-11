// Camera + handdetectie: MediaPipe HandLandmarker (WASM), volledig lokaal
// gebundeld in vendor/ — er gaat niets het netwerk over.
//
// De detectie draait in een Web Worker op verkleinde frames (640×360: scherp
// genoeg voor een nauwkeurige vingertop, ook als het kind wat verder af staat), zodat de renderlus er nooit op hoeft te wachten.
// We gebruiken alléén de wijsvingertop (landmark 8): met één vinger volgen
// voelt veel natuurlijker en preciezer dan met een hele hand.

const INFER_W = 640, INFER_H = 360;

export class Handen {
  constructor(video, voorkeur = null) {
    this.video = video;
    this.voorkeur = voorkeur;  // "CPU"/"GPU" afdwingen (?delegate=…), anders auto
    this.vingers = [];      // [{x, y}] genormaliseerd, al gespiegeld
    this.worker = null;
    this._bezig = false;    // hooguit één frame tegelijk onderweg
    this._lastVideoTime = -1;
    this._lastTs = 0;
    // diagnostiek (?fps=1): welke delegate, hoe snel, hoe vaak
    this.delegate = "?";
    this.detectMs = 0;
    this.detectHz = 0;
    this._telling = 0;
    this._telT0 = performance.now();
  }

  async start() {
    await Promise.all([this._startCamera(), this.laadModel()]);
  }

  _startCamera() {
    return navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
      audio: false,
    }).then(stream => new Promise(klaar => {
      this.video.srcObject = stream;
      this.video.play().catch(() => {});  // sommige browsers zeuren, beeld komt toch
      // nieuw-frame-signaal: requestVideoFrameCallback is betrouwbaar per frame;
      // video.currentTime tikt in sommige browsers veel te grof en dan zakt de
      // detectie (en dus de vinger) naar een slakkengang terwijl het beeld vlot oogt
      if (this.video.requestVideoFrameCallback) {
        const tik = () => {
          this._nieuwFrame = true;
          this.video.requestVideoFrameCallback(tik);
        };
        this.video.requestVideoFrameCallback(tik);
        this._heeftRVFC = true;
      }
      const af = () => { console.log("sterrenlijnen: camera klaar"); klaar(); };
      if (this.video.readyState >= 2) return af();
      this.video.addEventListener("loadeddata", af, { once: true });
      setTimeout(af, 4000);  // uiterste geval: start gewoon, de lus wacht wel op beeld
    }));
  }

  // Het model (20 MB wasm + gewichten) mag al laden terwijl het startscherm
  // nog staat; na een fout begint een volgende poging opnieuw.
  laadModel() {
    return this._model ??= this._laadModel().catch(e => {
      this._model = null;
      this.worker?.terminate();
      this.worker = null;
      throw e;
    });
  }

  _laadModel() {
    return this.voorkeur === "hoofd"
      ? this._startHoofddraad()  // ?delegate=hoofd: direct zonder worker
      : new Promise((klaar, fout) => {
      this.worker = new Worker("js/handworker.js");  // klassiek, zie handworker.js
      this.worker.onmessage = e => {
        if (e.data.type === "klaar") {
          this.delegate = e.data.delegate;
          console.log(`sterrenlijnen: handmodel klaar (${this.delegate})`);
          klaar();
        } else if (e.data.type === "fout") {
          fout(new Error(e.data.fout));
        } else if (e.data.type === "traag") {
          // worker-"GPU" blijkt software (traag): probeer echte GPU op de
          // hoofdthread; lukt dat niet, dan CPU-wasm in de worker
          console.log(`sterrenlijnen: worker-GPU traag (${e.data.mediaan.toFixed(0)} ms), ` +
                      "wissel naar hoofdthread-GPU");
          this._startHoofddraad().catch(() => {
            this.worker?.postMessage({ type: "wissel", naar: "CPU" });
          });
        } else if (e.data.type === "vingers") {
          if (!this._hoofdLm) {  // na de wissel negeren we nakomertjes
            this.delegate = e.data.delegate ?? this.delegate;
            this._verwerk(e.data.vingers, e.data.ms);
          }
          this._bezig = false;
        }
      };
      this.worker.onerror = err => fout(err);
      this.worker.postMessage({ type: "init", voorkeur: this.voorkeur,
                          traagMs: this.traagMs });
    });
  }

  async _startHoofddraad() {
    // De UMD-bundel als gewone <script> laden (de hoofdmodule is ESM, maar
    // de bundel zet zichzelf als global Vision) en GPU op de hoofdthread
    // proberen — daar praat WebGL wél met de echte videokaart.
    if (!window.Vision) {
      await new Promise((r, e) => {
        const s = document.createElement("script");
        s.src = "vendor/tasks-vision/vision_bundle.js";
        s.onload = r;
        s.onerror = () => e(new Error("bundel laadt niet"));
        document.head.appendChild(s);
      });
    }
    const files = await window.Vision.FilesetResolver.forVisionTasks("vendor/tasks-vision/wasm");
    const lm = await window.Vision.HandLandmarker.createFromOptions(files, {
      baseOptions: { modelAssetPath: "vendor/hand_landmarker.task", delegate: "GPU" },
      runningMode: "VIDEO",
      numHands: 2,
      minHandDetectionConfidence: 0.4,
      minTrackingConfidence: 0.4,
    });
    this._hoofdLm = lm;
    this.delegate = "GPU·hoofd";
    const w = this.worker;
    this.worker = null;
    this._bezig = false;
    w?.terminate();
    console.log("sterrenlijnen: handmodel draait nu op de hoofdthread (GPU)");
  }

  _verwerk(vingers, ms) {
    this.vingers = vingers;
    this.detectMs = this.detectMs * 0.8 + ms * 0.2;
    if (++this._telling === 20) {
      const nu = performance.now();
      this.detectHz = 20000 / (nu - this._telT0);
      this._telling = 0;
      this._telT0 = nu;
    }
  }

  _pakBitmap(v) {
    // createImageBitmap met resize is het snelst, maar niet elke browser
    // (Firefox!) kan dat — dan verkleinen we zelf via een OffscreenCanvas.
    if (!this._geenResize) {
      return createImageBitmap(v, { resizeWidth: INFER_W, resizeHeight: INFER_H,
                                    resizeQuality: "low" })
        .catch(err => {
          this._geenResize = true;
          return this._pakBitmap(v);
        });
    }
    if (!this._canvas) {
      this._canvas = new OffscreenCanvas(INFER_W, INFER_H);
      this._cctx = this._canvas.getContext("2d");
    }
    this._cctx.drawImage(v, 0, 0, INFER_W, INFER_H);
    return Promise.resolve(this._canvas.transferToImageBitmap());
  }

  update() {
    const v = this.video;
    if ((!this.worker && !this._hoofdLm) || this._bezig || v.readyState < 2) return;
    if (this._heeftRVFC) {
      if (!this._nieuwFrame) return;
      this._nieuwFrame = false;
    } else if (v.currentTime === this._lastVideoTime) {
      return;
    }
    this._lastVideoTime = v.currentTime;
    this._bezig = true;
    const ts = Math.max(this._lastTs + 1, Math.round(performance.now()));
    this._lastTs = ts;
    this._pakBitmap(v)
      .then(bitmap => {
        if (this._hoofdLm) {  // hoofdthread-pad: klein plaatje, echte GPU
          const t0 = performance.now();
          let vingers = [];
          try {
            const res = this._hoofdLm.detectForVideo(bitmap, ts);
            vingers = (res.landmarks || []).map(lm => ({ x: 1 - lm[8].x, y: lm[8].y }));
          } catch { /* enkel frame overslaan */ }
          bitmap.close();
          this._verwerk(vingers, performance.now() - t0);
          this._bezig = false;
        } else {
          this.worker.postMessage({ type: "frame", bitmap, ts }, [bitmap]);
        }
      })
      .catch(() => { this._bezig = false; });
  }
}
