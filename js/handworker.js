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
let TRAAG_MS = 45;      // GPU trager dan dit? dan is hij nep (softwarepad/leesstall)
const PROEF_N = 12;     // aantal frames om dat over te meten
let landmarker = null;
let delegate = "GPU";
let files = null;
let tijden = [];
let gewisseld = false;

async function maak(gewenst) {
  const opts = {
    baseOptions: { modelAssetPath: MODEL, delegate: gewenst },
    runningMode: "VIDEO",
    numHands: 2,
    minHandDetectionConfidence: 0.4,
    minTrackingConfidence: 0.4,
  };
  const lm = await HandLandmarker.createFromOptions(files, opts);
  delegate = gewenst;
  return lm;
}

self.onmessage = async e => {
  const d = e.data;
  if (d.type === "init") {
    try {
      if (typeof d.traagMs === "number") TRAAG_MS = d.traagMs;  // testhaakje
      files = await FilesetResolver.forVisionTasks(WASM_MAP);
      const voorkeur = d.voorkeur === "CPU" ? ["CPU"] : ["GPU", "CPU"];
      let laatste = null;
      for (const g of voorkeur) {
        try { landmarker = await maak(g); break; }
        catch (err) { laatste = err; }
      }
      if (!landmarker) throw laatste;
      self.postMessage({ type: "klaar", delegate });
    } catch (err) {
      self.postMessage({ type: "fout", fout: String(err) });
    }
    return;
  }
  if (d.type === "frame" && landmarker) {
    let vingers = [];
    const t0 = performance.now();
    try {
      const res = landmarker.detectForVideo(d.bitmap, d.ts);
      vingers = (res.landmarks || []).map(lm => ({ x: 1 - lm[TIP].x, y: lm[TIP].y }));
    } catch { /* enkel frame overslaan */ }
    d.bitmap.close();
    const ms = performance.now() - t0;
    self.postMessage({ type: "vingers", vingers, ms, delegate });
    // Sommige drivers geven in een worker een "GPU" die stiekem software is
    // of onder last inzakt naar 70-110 ms per frame — soms pas ná de eerste
    // seconden. Blijf daarom doorlopend meten (glijdend venster) en waarschuw
    // de hoofdthread zodra de mediaan te hoog wordt: die schakelt dan over op
    // main-thread-GPU (daar is WebGL wél echt).
    if (!gewisseld && delegate === "GPU") {
      tijden.push(ms);
      if (tijden.length > PROEF_N) tijden.shift();
      if (tijden.length === PROEF_N) {
        const mediaan = tijden.slice().sort((a, b) => a - b)[PROEF_N >> 1];
        if (mediaan > TRAAG_MS) {
          gewisseld = true;
          self.postMessage({ type: "traag", mediaan });
        }
      }
    }
    return;
  }
  if (d.type === "wissel") {  // laatste redmiddel: CPU-wasm in de worker
    try {
      const oud = landmarker;
      landmarker = await maak(d.naar || "CPU");
      oud?.close();
      self.postMessage({ type: "klaar", delegate });
    } catch { /* dan maar blijven zoals het was */ }
  }
};
