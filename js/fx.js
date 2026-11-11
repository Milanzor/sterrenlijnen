// Effecten: gloeddeeltjes, popringen, confetti, vliegende sterren, vingersporen,
// sterrenhemel en vignet. Alles canvas-2D; additief via "lighter".

export const KLEUREN = {
  TEAL: "#5fe3c4", CORAL: "#ff6b6b", LILA: "#c5a0ff",
  SKY: "#78c8ff", LIME: "#beeb78", ROSE: "#ffa0d2", AMBER: "#ffc24a",
};
export const SPEELKLEUREN = [KLEUREN.TEAL, KLEUREN.CORAL, KLEUREN.LILA,
                             KLEUREN.SKY, KLEUREN.LIME, KLEUREN.ROSE];

// Schrijffont: Playwrite NL (Google/TypeTogether, OFL — meegebundeld in
// assets/), het lopende schoolschrift met lussen zoals kinderen in Nederland
// leren schrijven ("verbonden schrift", gebaseerd op het Primarium-onderzoek).
export const KIDSFONT = '"Playwrite NL", "Baloo 2", sans-serif';

// Gloedbolletjes vooraf renderen: createRadialGradient per frame per deeltje
// was een van de grootste framekosten.
const _gloedCache = new Map();
export function gloedSprite(kleur) {
  let c = _gloedCache.get(kleur);
  if (!c) {
    c = document.createElement("canvas");
    c.width = c.height = 64;
    const g = c.getContext("2d");
    const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, kleur);
    grad.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 64, 64);
    _gloedCache.set(kleur, c);
  }
  return c;
}

// Tekst met schaduw is duur om elk frame opnieuw te zetten; cache als canvas.
// Sprites worden op schermresolutie (dpr) gerenderd, anders zijn ze wazig;
// lw/lh zijn de maten in CSS-pixels.
const _tekstCache = new Map();
let _dpr = 1;
export function zetSpriteDpr(dpr) {
  if (dpr === _dpr) return;
  _dpr = dpr;
  _tekstCache.clear();
}

export function tekstSprite(tekst, px, kleur,
                            { gewicht = 800, schaduw = true, font = '"Baloo 2"' } = {}) {
  const sleutel = `${tekst}|${px}|${kleur}|${gewicht}|${schaduw}|${font}`;
  let c = _tekstCache.get(sleutel);
  if (!c) {
    if (_tekstCache.size > 80) _tekstCache.clear();  // simpele rem op de cache
    c = document.createElement("canvas");
    const g0 = c.getContext("2d");
    g0.font = `${gewicht} ${px}px ${font}`;
    const pad = Math.ceil(px * 0.5);
    c.lw = Math.ceil(g0.measureText(tekst).width) + pad * 2;
    // schrijfletters hebben lange stokken en lussen: ruimer opmeten
    c.lh = Math.ceil(px * (font.includes("Playwrite") ? 2.4 : 1.5));
    c.width = Math.ceil(c.lw * _dpr);
    c.height = Math.ceil(c.lh * _dpr);
    const g = c.getContext("2d");
    g.scale(_dpr, _dpr);
    g.font = `${gewicht} ${px}px ${font}`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    if (schaduw) {
      g.shadowColor = "rgba(0,0,0,0.55)";
      g.shadowBlur = px * 0.22 * _dpr;
    }
    g.fillStyle = kleur;
    g.fillText(tekst, c.lw / 2, c.lh / 2);
    _tekstCache.set(sleutel, c);
  }
  return c;
}

// Sprite gecentreerd op (cx, cy) tekenen, in CSS-pixels.
export function tekenSprite(ctx, spr, cx, cy, schaal = 1) {
  const w = spr.lw * schaal, h = spr.lh * schaal;
  ctx.drawImage(spr, cx - w / 2, cy - h / 2, w, h);
}

export function tekenSter(ctx, x, y, r, rot, kleur) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 5;
    const rr = i % 2 === 0 ? r : r * 0.45;
    ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
  }
  ctx.closePath();
  ctx.fillStyle = kleur;
  ctx.fill();
  ctx.restore();
}

export class Effecten {
  constructor() {
    this.deeltjes = [];   // gloed of confetti
    this.ringen = [];
    this.vliegers = [];   // sterren die naar de teller vliegen
  }

  gloed(x, y, kleur, n = 10, kracht = 1) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const sp = (120 + Math.random() * 300) * kracht;
      this.deeltjes.push({
        x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 60,
        leven: 0.35 + Math.random() * 0.35, max: 0.7, r: 5 + Math.random() * 6,
        kleur, soort: "gloed", zw: 380,
      });
    }
  }

  confetti(x, y, n = 12) {
    for (let i = 0; i < n; i++) {
      this.deeltjes.push({
        x, y, vx: (Math.random() - 0.5) * 560, vy: -120 - Math.random() * 380,
        leven: 0.7 + Math.random() * 0.6, max: 1.3, r: 7 + Math.random() * 5,
        kleur: SPEELKLEUREN[(Math.random() * SPEELKLEUREN.length) | 0],
        rot: Math.random() * 6, rotV: (Math.random() - 0.5) * 10,
        soort: "confetti", zw: 700,
      });
    }
  }

  ring(x, y, r, kleur) {
    this.ringen.push({ x, y, r0: r, leven: 0.3, max: 0.3, kleur });
  }

  vlieger(x, y, doelX, doelY) {
    this.vliegers.push({ sx: x, sy: y, x, y, tx: doelX, ty: doelY, t: 0, dur: 0.55 });
  }

  update(dt) {
    for (const p of this.deeltjes) {
      p.leven -= dt;
      p.vy += p.zw * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      if (p.rotV) p.rot += p.rotV * dt;
    }
    let n = 0;  // ter plekke opruimen: geen nieuwe array per frame
    for (const p of this.deeltjes) if (p.leven > 0) this.deeltjes[n++] = p;
    this.deeltjes.length = n;
    for (const r of this.ringen) r.leven -= dt;
    if (this.ringen.length) this.ringen = this.ringen.filter(r => r.leven > 0);
    let klaar = 0;
    for (const v of this.vliegers) {
      v.t += dt;
      const k = Math.min(1, v.t / v.dur);
      const e = k * k * (3 - 2 * k);
      v.x = v.sx + (v.tx - v.sx) * e;
      v.y = v.sy + (v.ty - v.sy) * e - Math.sin(k * Math.PI) * 80;
      if (k >= 1) klaar++;
    }
    if (klaar) this.vliegers = this.vliegers.filter(v => v.t < v.dur);
    return klaar;  // aantal sterren dat de teller bereikte (voor het bump-effect)
  }

  teken(ctx) {
    for (const r of this.ringen) {
      const k = 1 - r.leven / r.max;
      ctx.strokeStyle = r.kleur;
      ctx.globalAlpha = 1 - k;
      ctx.lineWidth = 6 * (1 - k) + 1;
      ctx.beginPath();
      ctx.arc(r.x, r.y, r.r0 * (1 + k * 1.1), 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    ctx.save();
    for (const p of this.deeltjes) {
      const k = Math.max(0, p.leven / p.max);
      if (p.soort === "gloed") {
        ctx.globalCompositeOperation = "lighter";
        ctx.globalAlpha = k;
        const d = p.r * 4.4;
        ctx.drawImage(gloedSprite(p.kleur), p.x - d / 2, p.y - d / 2, d, d);
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.globalAlpha = Math.min(1, k * 2);
        tekenSter(ctx, p.x, p.y, p.r, p.rot, p.kleur);
      }
    }
    ctx.restore();
    ctx.globalAlpha = 1;
    for (const v of this.vliegers) {
      tekenSter(ctx, v.x, v.y, 14, v.t * 6, KLEUREN.AMBER);
    }
  }
}

// Vingerspoor: kort lint van recente posities, vervaagt vanzelf.
export class Spoor {
  constructor() { this.punten = []; }

  voeg(x, y, nu) {
    this.punten.push({ x, y, t: nu });
    while (this.punten.length && nu - this.punten[0].t > 0.30) this.punten.shift();
  }

  teken(ctx, kleur, nu) {
    if (this.punten.length < 2) return;
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (let i = 1; i < this.punten.length; i++) {
      const a = this.punten[i - 1], b = this.punten[i];
      const k = 1 - (nu - b.t) / 0.30;
      ctx.strokeStyle = kleur;
      ctx.globalAlpha = 0.45 * k * k;
      ctx.lineWidth = 2 + 9 * k;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }
    ctx.restore();
  }
}

// Achtergrondlaag (vignet + sterren): één keer per resize op een eigen canvas
// achter het spel, in plaats van elk frame schermvullend over te tekenen.
export function tekenHemel(canvas, W, H, dpr, n = 90) {
  canvas.width = Math.round(W * dpr);
  canvas.height = Math.round(H * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.32,
                                     W / 2, H / 2, Math.hypot(W, H) * 0.62);
  g.addColorStop(0, "rgba(13,12,34,0.30)");
  g.addColorStop(1, "rgba(13,12,34,0.85)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#fff";
  for (let i = 0; i < n; i++) {
    const x = Math.random() * W, y = Math.random() * H;
    const rand = Math.min(x, W - x) / W + Math.min(y, H - y) / H;
    if (Math.random() < rand * 2.2) continue;  // het midden is voor het kind
    ctx.globalAlpha = 0.25 + Math.random() * 0.4;
    ctx.beginPath();
    ctx.arc(x, y, Math.random() < 0.75 ? 1 : 2, 0, Math.PI * 2);
    ctx.fill();
  }
}
