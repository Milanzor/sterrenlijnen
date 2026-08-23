// Camera + handdetectie in de browser: MediaPipe HandLandmarker (WASM),
// volledig lokaal gebundeld in vendor/ — er gaat niets het netwerk over.
//
// We gebruiken alléén de wijsvingertop (landmark 8): met één vinger volgen
// voelt veel natuurlijker en preciezer dan met een hele hand.

import { FilesetResolver, HandLandmarker } from "../vendor/tasks-vision/vision_bundle.mjs";

const TIP = 8;

export class Handen {
  constructor(video) {
    this.video = video;
    this.landmarker = null;
    this.vingers = [];      // [{x, y}] genormaliseerd, al gespiegeld
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

    const modelKlaar = (async () => {
      const files = await FilesetResolver.forVisionTasks("vendor/tasks-vision/wasm");
      const opts = delegate => ({
        baseOptions: { modelAssetPath: "vendor/hand_landmarker.task", delegate },
        runningMode: "VIDEO",
        numHands: 2,
        minHandDetectionConfidence: 0.4,
        minTrackingConfidence: 0.4,
      });
      try {
        this.landmarker = await HandLandmarker.createFromOptions(files, opts("GPU"));
      } catch {
        this.landmarker = await HandLandmarker.createFromOptions(files, opts("CPU"));
      }
      console.log("sterrenlijnen: handmodel klaar");
    })();

    await Promise.all([cameraKlaar, modelKlaar]);
  }

  update() {
    const v = this.video;
    if (!this.landmarker || v.readyState < 2 || v.currentTime === this._lastVideoTime) return;
    this._lastVideoTime = v.currentTime;
    const ts = Math.max(this._lastTs + 1, Math.round(performance.now()));
    this._lastTs = ts;
    let res;
    try {
      res = this.landmarker.detectForVideo(v, ts);
    } catch {
      return;
    }
    this.vingers = (res.landmarks || []).map(lm => ({
      x: 1 - lm[TIP].x,  // spiegelen: het scherm is een spiegel
      y: lm[TIP].y,
    }));
  }
}
