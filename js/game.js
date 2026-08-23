// Het spel: figuren van stipjes natrekken met je wijsvinger — en bij
// duo-figuren met twee vingers tegelijk, één per lijn.
//
// Duo-regel: een lijn mag maar een paar stipjes vóórlopen op de andere.
// Loop je te ver voor, dan "wacht" jouw volgende stipje tot je andere hand
// heeft bijgehaald — zo ontstaat vanzelf het samen-bewegen.

import { makeQueue, refillQueue, fitPaths } from "./figures.js";
import { KLEUREN, SPEELKLEUREN, tekenSter } from "./fx.js";

const AHEAD = 2;      // stipjes vooruit mogen (tegen wild zwaaien)
const LEAD_MAX = 2;   // duo: zoveel stipjes mag de ene lijn voorlopen
const STARS_PER_LEVEL = 12;

export class SpoorSpel {
  constructor(W, H, fx, geluid, { duoEerst = false } = {}) {
    this.W = W; this.H = H;
    this.fx = fx;
    this.geluid = geluid;
    this.sterren = 0;
    this.level = 1;
    this.levelBannerT = 0;
    this.queue = makeQueue();
    if (duoEerst) this.queue.sort((a, b) => b.duo - a.duo);
    this.doneT = 0;
    this.sweepT = -1;
    this.lastLit = performance.now() / 1000;
    this.duoHintT = 0;
    this.waitPulse = [0, 0];
    this._lastWaitTik = 0;
    this.nieuwFiguur();
  }

  resize(W, H) { this.W = W; this.H = H; this.nieuwFiguur(this.figuur); }

  get hudSterPos() { return [this.W - 130, 54]; }

  nieuwFiguur(zelfde = null) {
    if (!this.queue.length) this.queue = refillQueue();
    const spec = zelfde ?? this.queue.shift();
    this.figuur = spec;
    const spacing = this.H * 0.082;
    const fitted = fitPaths(spec.paths, this.W, this.H, spacing);
    let kleuren;
    if (spec.duo) {
      const i = (Math.random() * SPEELKLEUREN.length) | 0;
      kleuren = [SPEELKLEUREN[i], SPEELKLEUREN[(i + 2) % SPEELKLEUREN.length]];
    } else {
      kleuren = [SPEELKLEUREN[(Math.random() * SPEELKLEUREN.length) | 0]];
    }
    this.paden = fitted.map((dots, i) => ({
      dots,
      lit: dots.map(() => false),
      litAt: dots.map(() => 0),
      progress: 0,
      kleur: kleuren[i],
      lastLitTime: 0,
    }));
    this.doneT = 0;
    this.sweepT = -1;
    this.lastLit = performance.now() / 1000;
    this.duoHintT = 0;
  }

  get klaar() { return this.paden.every(p => p.progress >= p.dots.length); }

  // vingers: [{x, y, px, py}] in schermcoördinaten, gesorteerd komt hier niet binnen
  update(dt, vingers, nu) {
    this.levelBannerT = Math.max(0, this.levelBannerT - dt);
    this.waitPulse = this.waitPulse.map(v => Math.max(0, v - dt));
    if (this.doneT > 0) {
      this.doneT -= dt;
      this.sweepT += dt;
      if (this.doneT <= 0) this.nieuwFiguur();
      return;
    }

    const duo = this.figuur.duo;
    if (duo) {
      this.duoHintT = vingers.length < 2 ? this.duoHintT + dt : 0;
    }
    const toewijzing = this._wijsToe(vingers);
    for (const [vinger, padIdx] of toewijzing) {
      vinger.padIdx = padIdx;
      this._trekken(vinger, padIdx, nu);
    }
    if (this.klaar) this._afgerond();
  }

  _wijsToe(vingers) {
    // → [vinger, padIndex]-paren. Enkel figuur: elke vinger mag het pad
    // trekken. Duo: linkervinger → linkerlijn, rechtervinger → rechterlijn.
    if (!this.figuur.duo) return vingers.map(v => [v, 0]);
    const sorted = vingers.slice().sort((a, b) => a.x - b.x);
    if (sorted.length >= 2) {
      return [[sorted[0], 0], [sorted[sorted.length - 1], 1]];
    }
    if (sorted.length === 1) {
      const v = sorted[0];
      const dichtst = this.paden
        .map((p, i) => [i, this._afstandTotVolgende(p, v)])
        .sort((a, b) => a[1] - b[1])[0][0];
      return [[v, dichtst]];
    }
    return [];
  }

  _afstandTotVolgende(pad, v) {
    if (pad.progress >= pad.dots.length) return 1e9;
    const [dx, dy] = pad.dots[pad.progress];
    return (dx - v.x) ** 2 + (dy - v.y) ** 2;
  }

  _trekken(v, padIdx, nu) {
    const pad = this.paden[padIdx];
    const ander = this.paden.length > 1 ? this.paden[1 - padIdx] : null;
    const HIT2 = (this.H * 0.062) ** 2;
    const pts = [[v.x, v.y], [(v.x + v.px) / 2, (v.y + v.py) / 2]];
    const tot = Math.min(pad.progress + 1 + AHEAD, pad.dots.length);
    for (let i = pad.progress; i < tot; i++) {
      if (pad.lit[i]) continue;
      const [dx, dy] = pad.dots[i];
      if (!pts.some(([px, py]) => (px - dx) ** 2 + (py - dy) ** 2 < HIT2)) continue;
      if (ander && this._aantalLit(pad) - this._aantalLit(ander) >= LEAD_MAX) {
        // wacht op je andere hand: zachte puls + heel af en toe een tikje
        this.waitPulse[padIdx] = 0.6;
        if (nu - this._lastWaitTik > 1.2) {
          this._lastWaitTik = nu;
          this.geluid.wacht();
        }
        continue;
      }
      pad.lit[i] = true;
      pad.litAt[i] = nu;
      pad.lastLitTime = nu;
      this.lastLit = nu;
      this.geluid.pop(this.figuur.duo && padIdx === 1);
      this.fx.gloed(dx, dy, pad.kleur, 4, 0.5);
    }
    while (pad.progress < pad.dots.length && pad.lit[pad.progress]) pad.progress++;
  }

  _aantalLit(pad) { return pad.lit.reduce((a, b) => a + (b ? 1 : 0), 0); }

  _afgerond() {
    const duo = this.figuur.duo;
    this.geluid.glinster();
    this.geluid.tada();
    for (const pad of this.paden) {
      pad.dots.forEach(([x, y], i) => {
        if (i % 2 === 0) this.fx.confetti(x, y, 3);
      });
      const [lx, ly] = pad.dots[pad.dots.length - 1];
      const n = duo ? 2 : 3;  // per pad; duo-totaal wordt zo 4 + bonus
      for (let i = 0; i < n; i++) this.fx.vlieger(lx + i * 18, ly, ...this.hudSterPos);
    }
    const winst = duo ? 5 : 3;  // duo = 2×2 vliegers + bonusster
    if (duo) this.fx.vlieger(this.W / 2, this.H * 0.4, ...this.hudSterPos);
    this._sterrenErbij(winst);
    this.doneT = 1.9;
    this.sweepT = 0;
  }

  _sterrenErbij(n) {
    this.sterren += n;
    const nieuw = Math.floor(this.sterren / STARS_PER_LEVEL) + 1;
    if (nieuw !== this.level) {
      this.level = nieuw;
      this.levelBannerT = 2.2;
      this.geluid.fanfare();
      for (let i = 0; i < 24; i++) this.fx.confetti(this.W / 2, this.H * 0.35, 1);
    }
  }

  // ---------- tekenen ----------

  teken(ctx, nu) {
    const duo = this.figuur.duo;
    for (const [i, pad] of this.paden.entries()) {
      this._tekenPad(ctx, pad, i, nu);
    }
    // figuurnaam bovenin (bounce'je zolang het figuur net af is)
    const naam = this.figuur.name + (duo ? "  ✦ twee handen!" : "");
    const schaal = this.doneT > 0 ? 1 + Math.sin(Math.min(1, this.sweepT / 0.3) * Math.PI) * 0.18 : 1;
    ctx.save();
    ctx.translate(this.W / 2, this.H * 0.15);
    ctx.scale(schaal, schaal);
    ctx.font = `800 ${Math.round(this.H * 0.055)}px "Baloo 2"`;
    ctx.textAlign = "center";
    ctx.fillStyle = this.paden[0].kleur;
    ctx.shadowColor = "rgba(0,0,0,0.5)";
    ctx.shadowBlur = 12;
    ctx.fillText(naam, 0, 0);
    ctx.restore();

    if (duo && this.duoHintT > 2.5 && this.doneT <= 0) {
      this._pulsTekst(ctx, "Gebruik allebei je handen!", nu);
    } else if (nu - this.lastLit > 8 && this.doneT <= 0) {
      this._pulsTekst(ctx, "Volg de stipjes met je wijsvinger!", nu);
    }
    if (this.levelBannerT > 0) this._tekenLevelBanner(ctx);
  }

  _tekenPad(ctx, pad, padIdx, nu) {
    const { dots, lit, progress, kleur } = pad;
    if (dots.length < 2) return;
    // vage voorbeeldlijn
    ctx.strokeStyle = "rgba(120,124,165,0.55)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    dots.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.stroke();
    // het al gevolgde stuk, met gloed
    if (progress >= 2) {
      ctx.save();
      ctx.strokeStyle = kleur;
      ctx.lineWidth = 7;
      ctx.lineJoin = "round";
      ctx.shadowColor = kleur;
      ctx.shadowBlur = 14;
      ctx.beginPath();
      for (let i = 0; i < progress; i++) {
        const [x, y] = dots[i];
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
      ctx.restore();
    }
    // afrondings-animatie: een lichtstreep raast over de hele lijn
    if (this.sweepT >= 0 && this.sweepT < 0.9) {
      const kop = this.sweepT / 0.9 * dots.length;
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 10;
      ctx.shadowColor = "#fff";
      ctx.shadowBlur = 22;
      ctx.beginPath();
      for (let i = Math.max(0, Math.floor(kop) - 4); i < Math.min(dots.length, Math.ceil(kop)); i++) {
        const [x, y] = dots[i];
        ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.restore();
    }
    // stipjes
    for (let i = 0; i < dots.length; i++) {
      const [x, y] = dots[i];
      if (lit[i]) {
        const flits = Math.max(0, 0.35 - (nu - pad.litAt[i])) / 0.35;
        ctx.fillStyle = "#fff";
        ctx.beginPath();
        ctx.arc(x, y, 8 + flits * 7, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.strokeStyle = "rgba(205,209,238,0.9)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
    // markeer de volgende stip: pulserende ring + draaiend sterretje
    if (this.doneT <= 0 && progress < dots.length) {
      const [x, y] = dots[progress];
      const wacht = this.waitPulse[padIdx] > 0;
      const rr = 24 + Math.sin(nu * 5) * 5 + (wacht ? 8 : 0);
      ctx.strokeStyle = wacht ? "rgba(255,194,74,0.5)" : KLEUREN.AMBER;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(x, y, rr, 0, Math.PI * 2);
      ctx.stroke();
      tekenSter(ctx, x, y, wacht ? 12 : 16, nu * 1.2, KLEUREN.AMBER);
      if (wacht) {  // wacht op je andere hand
        ctx.font = `700 ${Math.round(this.H * 0.026)}px "Baloo 2"`;
        ctx.textAlign = "center";
        ctx.fillStyle = KLEUREN.AMBER;
        ctx.fillText("wacht op je andere hand…", x, y - rr - 12);
      }
    }
  }

  _pulsTekst(ctx, tekst, nu) {
    const puls = 0.5 + 0.5 * Math.sin(nu * 2.6);
    ctx.font = `800 ${Math.round(this.H * 0.045)}px "Baloo 2"`;
    ctx.textAlign = "center";
    ctx.globalAlpha = 0.6 + 0.4 * puls;
    ctx.fillStyle = "#fff";
    ctx.shadowColor = "rgba(0,0,0,0.6)";
    ctx.shadowBlur = 10;
    ctx.fillText(tekst, this.W / 2, this.H * 0.88);
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
  }

  _tekenLevelBanner(ctx) {
    const k = Math.min(1, (2.2 - this.levelBannerT) / 0.25);
    const alpha = this.levelBannerT > 0.5 ? 1 : this.levelBannerT / 0.5;
    ctx.save();
    ctx.translate(this.W / 2, this.H * 0.30);
    ctx.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k);
    ctx.globalAlpha = alpha;
    ctx.font = `800 ${Math.round(this.H * 0.09)}px "Baloo 2"`;
    ctx.textAlign = "center";
    ctx.fillStyle = KLEUREN.AMBER;
    ctx.shadowColor = "rgba(0,0,0,0.5)";
    ctx.shadowBlur = 16;
    ctx.fillText(`Level ${this.level}!`, 0, 0);
    ctx.restore();
  }
}
