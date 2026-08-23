// Sterrenlijnen — lijnen volgen met je wijsvinger, voor de browser.
// Camera → MediaPipe-handdetectie → soepele vingercursors → het spel.
//
// ?demo=1 slaat de camera over en laat twee spookvingers vanzelf spelen
// (handig om te testen, en meteen een leuke demostand).

import { Handen } from "./hands.js";
import { SpoorSpel } from "./game.js";
import { LEVELS } from "./figures.js";
import { LETTERS } from "./letters.js";
import { Effecten, Spoor, KLEUREN, tekenSter, gloedSprite, tekstSprite,
         maakSterrenhemel, maakVignet } from "./fx.js";
import { Geluid } from "./audio.js";

const canvas = document.getElementById("scherm");
const ctx = canvas.getContext("2d");
const video = document.getElementById("cam");
const overlay = document.getElementById("overlay");
const foutEl = document.getElementById("foutmelding");
const DEMO = new URLSearchParams(location.search).has("demo");
const TOON_FPS = new URLSearchParams(location.search).has("fps");
let renderFps = 0, _fpsN = 0, _fpsT0 = performance.now();

let W = 0, H = 0, dpr = 1;
let handen = null, spel = null, fx = null, geluid = null;
let sterrenhemel = null, vignet = null;
let vingers = [];      // gladgestreken cursors [{x,y,px,py,doelX,doelY,gezien,spoor,padIdx}]
let scoreBump = 0;
let laatsteFrame = performance.now();

function maat() {
  dpr = Math.min(window.devicePixelRatio || 1, 1.5);
  W = window.innerWidth;
  H = window.innerHeight;
  canvas.width = Math.round(W * dpr);
  canvas.height = Math.round(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  sterrenhemel = maakSterrenhemel(W, H);
  vignet = maakVignet(W, H);
  if (spel) spel.resize(W, H);
}
window.addEventListener("resize", maat);
maat();

// ---------- vingercursors: 30 Hz-detectie → soepel op schermtempo ----------

const SMOOTH_K = 22;

function updateVingers(dt, nu) {
  const targets = DEMO ? demoVingers(nu)
                       : handen.vingers.map(v => camNaarScherm(v.x, v.y));

  // koppel detecties aan bestaande cursors op afstand
  const vrij = new Set(vingers.map((_, i) => i));
  for (const t of targets) {
    let best = -1, bestD = 1e18;
    for (const i of vrij) {
      const d = (vingers[i].x - t.x) ** 2 + (vingers[i].y - t.y) ** 2;
      if (d < bestD) { bestD = d; best = i; }
    }
    if (best >= 0 && bestD < 420 ** 2) {
      const v = vingers[best];
      v.doelX = t.x; v.doelY = t.y; v.gezien = nu;
      vrij.delete(best);
    } else {
      vingers.push({ x: t.x, y: t.y, px: t.x, py: t.y, doelX: t.x, doelY: t.y,
                     gezien: nu, spoor: new Spoor(), padIdx: 0 });
    }
  }
  vingers = vingers.filter(v => nu - v.gezien < 0.35);
  const k = 1 - Math.exp(-dt * SMOOTH_K);
  for (const v of vingers) {
    v.px = v.x; v.py = v.y;
    v.x += (v.doelX - v.x) * k;
    v.y += (v.doelY - v.y) * k;
    v.spoor.voeg(v.x, v.y, nu);
  }
}

// camerabeeld dekt het scherm (cover-fit, gecentreerd)
let dekking = { schaal: 1, ox: 0, oy: 0, vw: 1280, vh: 720 };

function updateDekking() {
  const vw = video.videoWidth || 1280, vh = video.videoHeight || 720;
  const schaal = Math.max(W / vw, H / vh);
  dekking = { schaal, vw, vh, ox: (W - vw * schaal) / 2, oy: (H - vh * schaal) / 2 };
}

function camNaarScherm(nx, ny) {
  return { x: nx * dekking.vw * dekking.schaal + dekking.ox,
           y: ny * dekking.vh * dekking.schaal + dekking.oy };
}

// ---------- demostand: twee spookvingers spelen vanzelf ----------

function demoVingers(nu) {
  if (!spel) return [];
  const doelen = [];
  const paden = spel.paden;
  // duo: één spookvinger per lijn; strokes (letters): de haal die aan de
  // beurt is; anders gewoon het ene pad
  const idxs = spel.figuur.duo ? [0, 1]
             : spel.figuur.strokes ? [spel.actieveHaal] : [0];
  for (const [i, pi] of idxs.entries()) {
    const pad = paden[Math.min(pi, paden.length - 1)];
    const idx = Math.min(pad.progress, pad.dots.length - 1);
    const [dx, dy] = pad.dots[idx];
    doelen.push({ x: dx + Math.sin(nu * 3 + i * 7) * 6, y: dy + Math.cos(nu * 2.6 + i) * 6 });
  }
  return doelen;
}

// ---------- hoofdlus ----------

function lus() {
  requestAnimationFrame(lus);
  const nuMs = performance.now();
  const dt = Math.min((nuMs - laatsteFrame) / 1000, 0.05);
  laatsteFrame = nuMs;
  const nu = nuMs / 1000;

  if (!DEMO) {
    handen.update();
    updateDekking();
  }
  updateVingers(dt, nu);
  spel.update(dt, vingers, nu);
  scoreBump = Math.max(0, scoreBump - dt);
  scoreBump += fx.update(dt) ? 0.25 : 0;

  teken(nu);
}

function teken(nu) {
  ctx.fillStyle = "#05070f";
  ctx.fillRect(0, 0, W, H);
  if (!DEMO && video.readyState >= 2) {
    ctx.save();  // spiegelen: het scherm is een spiegel
    ctx.translate(W, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, -dekking.ox - dekking.vw * dekking.schaal + W, dekking.oy,
                  dekking.vw * dekking.schaal, dekking.vh * dekking.schaal);
    ctx.restore();
  }
  ctx.drawImage(vignet, 0, 0);
  ctx.drawImage(sterrenhemel, 0, 0);

  spel.teken(ctx, nu);
  fx.teken(ctx);

  // duo-samenspel: glinsterlijn tussen je twee vingers als beide lijnen lopen
  if (spel.figuur.duo && vingers.length >= 2) {
    const [a, b] = vingers;
    const samen = spel.paden.every(p => nu - p.lastLitTime < 1.5 && p.lastLitTime > 0);
    if (samen) {
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      const g = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
      g.addColorStop(0, spel.paden[0].kleur);
      g.addColorStop(1, spel.paden[spel.paden.length - 1].kleur);
      ctx.strokeStyle = g;
      ctx.globalAlpha = 0.35 + 0.2 * Math.sin(nu * 8);
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.restore();
    }
  }

  // vingercursors: spoor + gloeiende punt in de kleur van hun lijn
  for (const v of vingers) {
    const kleur = spel.paden[Math.min(v.padIdx ?? 0, spel.paden.length - 1)].kleur;
    v.spoor.teken(ctx, kleur, nu);
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    ctx.drawImage(gloedSprite(kleur), v.x - 26, v.y - 26, 52, 52);
    ctx.restore();
    ctx.fillStyle = "#fff";
    ctx.beginPath();
    ctx.arc(v.x, v.y, 5, 0, Math.PI * 2);
    ctx.fill();
  }

  tekenHud(nu);
  if (TOON_FPS) {
    if (++_fpsN === 30) {
      const t = performance.now();
      renderFps = 30000 / (t - _fpsT0);
      _fpsN = 0; _fpsT0 = t;
    }
    const d = handen ?? {};
    ctx.font = '600 15px "Baloo 2"';
    ctx.textAlign = "left";
    ctx.fillStyle = "#9ff";
    ctx.fillText(`render ${renderFps.toFixed(0)} fps · detectie ${(d.detectHz ?? 0).toFixed(1)} Hz` +
                 ` · ${(d.detectMs ?? 0).toFixed(0)} ms · ${d.delegate ?? "-"}`, 14, H - 14);
    window.__diag = { renderFps, detectHz: d.detectHz, detectMs: d.detectMs, delegate: d.delegate };
  }
  if (!DEMO && vingers.length === 0 && nu - startTijd > 4) {
    const puls = 0.5 + 0.5 * Math.sin(nu * 2.4);
    const spr = tekstSprite("Wijs met je vinger naar het scherm!",
                            Math.round(H * 0.05), "#fff");
    ctx.globalAlpha = 0.6 + 0.4 * puls;
    ctx.drawImage(spr, W / 2 - spr.width / 2, H * 0.66 - spr.height / 2);
    ctx.globalAlpha = 1;
  }
}

function tekenHud(nu) {
  const [sx, sy] = spel.hudSterPos;
  tekenSter(ctx, sx, sy, 22 * (1 + scoreBump * 1.2), 0, KLEUREN.AMBER);
  ctx.font = `800 ${Math.round(H * 0.052)}px "Baloo 2"`;
  ctx.textAlign = "left";
  ctx.fillStyle = "#fff";
  ctx.fillText(String(spel.sterren), sx + 36, sy + 18);
  const lbl = tekstSprite(spel.levelLabel, Math.round(H * 0.024), "rgba(210,214,245,0.95)",
                          { gewicht: 600, schaduw: false });
  ctx.drawImage(lbl, W - 16 - lbl.width, sy + 26);
}

// ---------- opstarten ----------

let startTijd = 0;

async function start(modus = "level") {
  for (const b of document.querySelectorAll(".startknop")) b.disabled = true;
  try {  // font eerst, anders tekent het canvas de eerste tellen systeemfont
    await document.fonts.load('800 40px "Baloo 2"');
    if (modus === "letter") await document.fonts.load("700 40px Kermit");
  } catch { /* systeemfont is dan de fallback */ }
  geluid = new Geluid();
  geluid.init();
  fx = new Effecten();
  const params = new URLSearchParams(location.search);
  const lijst = modus === "letter" ? LETTERS : LEVELS;
  let startLevel = null;  // ?level=N springt naar dat level, ?duo naar het
                          // eerste duo, ?letter=b naar die letter
  if (params.has("level")) {
    startLevel = Math.max(0, Math.min(lijst.length - 1, (parseInt(params.get("level")) || 1) - 1));
  } else if (modus === "letter" && params.has("letter")) {
    const i = LETTERS.findIndex(f => f.letter === (params.get("letter") || "").toLowerCase());
    if (i >= 0) startLevel = i;
  } else if (modus === "level" && params.has("duo")) {
    startLevel = LEVELS.findIndex(f => f.duo);
  }
  spel = new SpoorSpel(W, H, fx, geluid, { startLevel, modus });
  const wissel = document.getElementById("wissel");
  wissel.textContent = modus === "letter" ? "⭐" : "🔤";
  wissel.title = modus === "letter" ? "Naar de Level modus" : "Naar de Letter leer modus";
  try {
    if (!DEMO) {
      const p2 = new URLSearchParams(location.search);
      handen = new Handen(video, p2.get("delegate"));
      if (p2.has("traag")) handen.traagMs = 0;  // testhaakje: forceer de wissel
      await handen.start();
    }
  } catch (e) {
    const msg = String((e && e.message) || e);
    foutEl.textContent = /NotAllowed|Permission|NotFound|NotReadable|OverconstrainedError/i.test(msg)
      ? `De camera lukt niet: ${msg} — controleer of de browser bij de camera mag.`
      : `Het laden lukt niet: ${msg} — probeer de pagina te verversen.`;
    foutEl.hidden = false;
    for (const b of document.querySelectorAll(".startknop")) b.disabled = false;
    return;
  }
  overlay.remove();
  document.getElementById("knoppen").hidden = false;
  startTijd = performance.now() / 1000;
  laatsteFrame = performance.now();
  window.__spel = spel;  // voor tests
  requestAnimationFrame(lus);
}

document.getElementById("start").addEventListener("click", () => start("level"));
document.getElementById("startLetters").addEventListener("click", () => start("letter"));
document.getElementById("wissel").addEventListener("click", () => {
  // herladen in de andere modus; auto=1 zodat je niet opnieuw hoeft te klikken
  const p = new URLSearchParams(location.search);
  spel?.modus === "letter" ? p.delete("letters") : p.set("letters", "1");
  p.delete("level");
  p.delete("letter");
  if (!DEMO) p.set("auto", "1");
  location.search = p.toString();
});
document.getElementById("geluid").addEventListener("click", e => {
  geluid.zetAan(!geluid.aan);
  e.target.textContent = geluid.aan ? "🔊" : "🔇";
});
document.getElementById("volscherm").addEventListener("click", () => {
  document.fullscreenElement ? document.exitFullscreen()
                             : document.documentElement.requestFullscreen();
});
document.getElementById("overslaan").addEventListener("click", () => spel?.slaOver());
// ?demo=1: geen camera, spookvingers spelen vanzelf; ?auto=1: meteen starten
// mét camera (voor tests met een nepcamera in headless browsers);
// ?letters=1 kiest daarbij de Letter leer modus
const _p = new URLSearchParams(location.search);
if (DEMO || _p.has("auto")) start(_p.has("letters") ? "letter" : "level");
