// Handdetectie in een aparte thread: de hoofdthread stuurt verkleinde
// videoframes (ImageBitmap) en krijgt vingertoppen terug. Zo kost de
// detectie (~10-20 ms per frame) nooit een render-frame.
//
// Bewust een KLASSIEKE worker (geen module): MediaPipe's wasm-loader zet
// zijn ModuleFactory als global en dat werkt alleen via importScripts —
// als ES-module blijft die module-lokaal ("ModuleFactory not set", Firefox).

importScripts("../vendor/tasks-vision/vision_bundle.js");

const { FilesetResolver, HandLandmarker } = Vision;
const TIP = 8;
// Absolute URL's: de bundel resolvet relatieve paden intern tegen zichzelf,
// niet tegen deze worker — dan krijg je "vendor/vendor/…".
const WASM_MAP = new URL("../vendor/tasks-vision/wasm", self.location.href).href;
const MODEL = new URL("../vendor/hand_landmarker.task", self.location.href).href;
let landmarker = null;

self.onmessage = async e => {
  const d = e.data;
  if (d.type === "init") {
    try {
      const files = await FilesetResolver.forVisionTasks(WASM_MAP);
      const opts = delegate => ({
        baseOptions: { modelAssetPath: MODEL, delegate },
        runningMode: "VIDEO",
        numHands: 2,
        minHandDetectionConfidence: 0.4,
        minTrackingConfidence: 0.4,
      });
      try {
        landmarker = await HandLandmarker.createFromOptions(files, opts("GPU"));
      } catch {
        landmarker = await HandLandmarker.createFromOptions(files, opts("CPU"));
      }
      self.postMessage({ type: "klaar" });
    } catch (err) {
      self.postMessage({ type: "fout", fout: String(err) });
    }
    return;
  }
  if (d.type === "frame" && landmarker) {
    let vingers = [];
    try {
      const res = landmarker.detectForVideo(d.bitmap, d.ts);
      vingers = (res.landmarks || []).map(lm => ({ x: 1 - lm[TIP].x, y: lm[TIP].y }));
    } catch { /* enkel frame overslaan */ }
    d.bitmap.close();
    self.postMessage({ type: "vingers", vingers });
  }
};
