// Handdetectie in een aparte thread: de hoofdthread stuurt verkleinde
// videoframes (ImageBitmap) en krijgt vingertoppen terug. Zo kost de
// detectie (~10-20 ms per frame) nooit een render-frame.

import { FilesetResolver, HandLandmarker } from "../vendor/tasks-vision/vision_bundle.mjs";

const TIP = 8;
let landmarker = null;

self.onmessage = async e => {
  const d = e.data;
  if (d.type === "init") {
    try {
      const files = await FilesetResolver.forVisionTasks("../vendor/tasks-vision/wasm");
      const opts = delegate => ({
        baseOptions: { modelAssetPath: "../vendor/hand_landmarker.task", delegate },
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
