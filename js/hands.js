// Camera + handdetectie: MediaPipe HandLandmarker (WASM), volledig lokaal
// gebundeld in vendor/ — er gaat niets het netwerk over.
//
// De detectie draait in een Web Worker op verkleinde frames (480×270, ruim
// genoeg voor vingertoppen), zodat de renderlus er nooit op hoeft te wachten.
// We gebruiken alléén de wijsvingertop (landmark 8): met één vinger volgen
// voelt veel natuurlijker en preciezer dan met een hele hand.

const INFER_W = 480, INFER_H = 270;

export class Handen {
  constructor(video) {
    this.video = video;
    this.vingers = [];      // [{x, y}] genormaliseerd, al gespiegeld
    this.worker = null;
    this._bezig = false;    // hooguit één frame tegelijk onderweg
    this._lastVideoTime = -1;
    this._lastTs = 0;
  }

  async start() {
    // camera en model tegelijk laden: scheelt merkbaar opstarttijd
    const cameraKlaar = navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
      audio: false,
    }).then(stream => new Promise(klaar => {
      this.video.srcObject = stream;
      this.video.play().catch(() => {});  // sommige browsers zeuren, beeld komt toch
      const af = () => { console.log("sterrenlijnen: camera klaar"); klaar(); };
      if (this.video.readyState >= 2) return af();
      this.video.addEventListener("loadeddata", af, { once: true });
      setTimeout(af, 4000);  // uiterste geval: start gewoon, de lus wacht wel op beeld
    }));

    const modelKlaar = new Promise((klaar, fout) => {
      this.worker = new Worker("js/handworker.js");  // klassiek, zie handworker.js
      this.worker.onmessage = e => {
        if (e.data.type === "klaar") {
          console.log("sterrenlijnen: handmodel klaar");
          klaar();
        } else if (e.data.type === "fout") {
          fout(new Error(e.data.fout));
        } else if (e.data.type === "vingers") {
          this.vingers = e.data.vingers;
          this._bezig = false;
        }
      };
      this.worker.onerror = err => fout(err);
      this.worker.postMessage({ type: "init" });
    });

    await Promise.all([cameraKlaar, modelKlaar]);
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
    if (!this.worker || this._bezig || v.readyState < 2
        || v.currentTime === this._lastVideoTime) return;
    this._lastVideoTime = v.currentTime;
    this._bezig = true;
    const ts = Math.max(this._lastTs + 1, Math.round(performance.now()));
    this._lastTs = ts;
    this._pakBitmap(v)
      .then(bitmap => this.worker.postMessage({ type: "frame", bitmap, ts }, [bitmap]))
      .catch(() => { this._bezig = false; });
  }
}
