// Het spel: figuren van stipjes natrekken met je wijsvinger — en bij
// duo-figuren met twee vingers tegelijk, één per lijn.
//
// Duo-regel: een lijn mag maar een paar stipjes vóórlopen op de andere.
// Loop je te ver voor, dan "wacht" jouw volgende stipje tot je andere hand
// heeft bijgehaald — zo ontstaat vanzelf het samen-bewegen.
//
// Drie modi: de Level modus (100 figuren), de Letter leer modus (a t/m z) en
// de Woorden modus (korte leeswoorden). Letters en woorden bestaan uit halen
// (strokes) die ná elkaar getrokken worden, in de echte schrijfvolgorde,
// tussen schrijflijnen.

import { LEVELS, fitPaths } from "./figures.js";
import { LETTERS } from "./letters.js";
import { WOORDEN } from "./words.js";
import { KLEUREN, SPEELKLEUREN, KIDSFONT, tekenSter, tekstSprite } from "./fx.js";

const AHEAD = 2;      // stipjes vooruit mogen (tegen wild zwaaien)
const LEAD_MAX = 2;   // duo: zoveel stipjes mag de ene lijn voorlopen
const OPSLAG = "sterrenlijnen";
const MODI = {
  level:  { lijst: LEVELS,  opslag: OPSLAG,              soort: "Level",  meervoud: "levels" },
  letter: { lijst: LETTERS, opslag: `${OPSLAG}-letters`, soort: "Letter", meervoud: "letters" },
  woord:  { lijst: WOORDEN, opslag: `${OPSLAG}-woorden`, soort: "Woord",  meervoud: "woorden" },
};

function laadVoortgang(sleutel, maxLevel) {
  try {
    const d = JSON.parse(localStorage.getItem(sleutel)) || {};
    return { level: Math.min(Math.max(d.level | 0, 0), maxLevel),
             sterren: Math.max(d.sterren | 0, 0) };
  } catch {
    return { level: 0, sterren: 0 };
  }
}

export class SpoorSpel {
  constructor(W, H, fx, geluid, { startLevel = null, modus = "level" } = {}) {
    this.W = W; this.H = H;
    this.fx = fx;
    this.geluid = geluid;
    this.modus = modus;
    this.levels = MODI[modus].lijst;
    this.opslag = MODI[modus].opslag;
    const opgeslagen = laadVoortgang(this.opslag, this.levels.length);
    this.levelIdx = startLevel ?? opgeslagen.level;  // 0-based; 100 = alles af
    this.sterren = startLevel === null ? opgeslagen.sterren : 0;
    this.levelBannerT = 0;
    this.doneT = 0;
    this.sweepT = -1;
    this.lastLit = performance.now() / 1000;
    this.duoHintT = 0;
    this.waitPulse = [0, 0];
    this._lastWaitTik = 0;
    this._vrijSpelIdx = null;  // na level 100: willekeurig figuur
    this.nieuwFiguur();
  }

  resize(W, H) { this.W = W; this.H = H; this.nieuwFiguur(this.figuur); }

  get hudSterPos() { return [this.W - 130, 54]; }

  get levelLabel() {
    const n = this.levels.length;
    return this.levelIdx < n ? `${MODI[this.modus].soort} ${this.levelIdx + 1}/${n}`
                             : `${n} ✓ · vrij spelen`;
  }

  bewaar() {
    try {
      localStorage.setItem(this.opslag, JSON.stringify(
        { level: this.levelIdx, sterren: this.sterren }));
    } catch { /* privémodus o.i.d.: dan even niet */ }
  }

  nieuwFiguur(zelfde = null) {
    let spec = zelfde;
    if (!spec) {
      if (this.levelIdx < this.levels.length) {
        spec = this.levels[this.levelIdx];
      } else {  // alles gehaald: vrij spelen, willekeurige volgorde
        let i;
        do { i = Math.floor(Math.random() * this.levels.length); }
        while (i === this._vrijSpelIdx);
        this._vrijSpelIdx = i;
        spec = this.levels[i];
      }
    }
    this.figuur = spec;
    const spacing = this.H * (spec.kader ? 0.07 : 0.082);
    const { paden: fitted, naarX, naarY, k } = fitPaths(spec.paths, this.W, this.H, spacing, spec.kader);
    if (spec.kader) {  // schrijflijnen: bovenlijn, x-hoogte, grondlijn
      let minX = Infinity, maxX = -Infinity;
      for (const p of spec.paths) for (const [x] of p) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
      }
      // de regel is minstens zo breed als bij een losse letter, en groeit
      // mee met een heel woord
      this.schrijflijnen = {
        x0: Math.min(naarX(minX) - k * 0.14, this.W / 2 - k * 0.52),
        x1: Math.max(naarX(maxX) + k * 0.14, this.W / 2 + k * 0.52),
        top: naarY(0.1), xh: naarY(0.5), grond: naarY(1.0), k,
      };
    }
    if (spec.zegNieuw && !zelfde) this.geluid.zeg(spec.zegNieuw);
    let kleuren;
    if (spec.duo) {
      const i = (Math.random() * SPEELKLEUREN.length) | 0;
      kleuren = [SPEELKLEUREN[i], SPEELKLEUREN[(i + 2) % SPEELKLEUREN.length]];
    } else if (spec.groepen) {  // woorden: elke letter zijn eigen kleur
      const basis = (Math.random() * SPEELKLEUREN.length) | 0;
      kleuren = spec.groepen.map(g => SPEELKLEUREN[(basis + g) % SPEELKLEUREN.length]);
    } else {  // strokes-figuren: alle halen in dezelfde kleur — het is één letter
      kleuren = [SPEELKLEUREN[(Math.random() * SPEELKLEUREN.length) | 0]];
    }
    this.paden = fitted.map((dots, i) => ({
      dots,
      lit: dots.map(() => false),
      litAt: dots.map(() => 0),
      progress: 0,
      kleur: kleuren[i] ?? kleuren[0],
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
      if (this.doneT <= 0) this._volgendLevel();
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

  get actieveHaal() {  // strokes-figuren: de eerste nog niet afgemaakte haal
    const i = this.paden.findIndex(p => p.progress < p.dots.length);
    return i < 0 ? this.paden.length - 1 : i;
  }

  _wijsToe(vingers) {
    // → [vinger, padIndex]-paren. Enkel figuur: elke vinger mag het pad
    // trekken. Strokes (letters): iedereen werkt aan de actieve haal, de
    // halen komen ná elkaar — dat ís de schrijfvolgorde.
    // Duo: linkervinger → linkerlijn, rechtervinger → rechterlijn.
    if (this.figuur.strokes) {
      const i = this.actieveHaal;
      return vingers.map(v => [v, i]);
    }
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
    const ander = this.figuur.duo && this.paden.length > 1 ? this.paden[1 - padIdx] : null;
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
    if (this.figuur.zegKlaar) this.geluid.zeg(this.figuur.zegKlaar);  // "a!" / "kat!"
    this.sterren += winst;
    this.doneT = 1.9;
    this.sweepT = 0;
  }

  _volgendLevel() {
    if (this.levelIdx < this.levels.length) {
      this.levelIdx++;
      this.levelBannerT = 2.0;
      if (this.levelIdx % 10 === 0 || this.levelIdx === this.levels.length) {
        // mijlpaal: elke tien levels een feestje
        this.geluid.fanfare();
        for (let i = 0; i < 24; i++) this.fx.confetti(this.W / 2, this.H * 0.35, 1);
      }
    }
    this.bewaar();
    this.nieuwFiguur();
  }

  slaOver() {  // voor als een figuur écht niet lukt (knopje voor papa/mama)
    if (this.doneT > 0) return;
    this.geluid.fizzle();
    this._volgendLevel();
  }

  // ---------- tekenen ----------

  teken(ctx, nu) {
    const duo = this.figuur.duo;
    const schrijf = !!this.figuur.kader;
    if (schrijf) this._tekenSchrijfregel(ctx);
    const actief = this.figuur.strokes ? this.actieveHaal : -1;
    for (const [i, pad] of this.paden.entries()) {
      this._tekenPad(ctx, pad, i, nu, actief);
    }
    // figuurnaam bovenin (bounce'je zolang het figuur net af is), uit de cache
    const naam = this.figuur.name + (duo ? "  ✦ twee handen!" : "");
    const spr = tekstSprite(naam, Math.round(this.H * 0.055), this.paden[0].kleur,
                            schrijf ? { font: KIDSFONT } : {});
    const schaal = this.doneT > 0 ? 1 + Math.sin(Math.min(1, this.sweepT / 0.3) * Math.PI) * 0.18 : 1;
    ctx.drawImage(spr, this.W / 2 - spr.width * schaal / 2,
                  this.H * 0.15 - spr.height * schaal / 2,
                  spr.width * schaal, spr.height * schaal);

    // voorbeeld naast de schrijfregel, in het kinderfont (Kermit):
    // de losse letter groot, een heel woord wat kleiner
    if (this.figuur.toon) {
      const px = Math.round(this.H * (this.figuur.toon.length > 1 ? 0.13 : 0.26));
      const vb = tekstSprite(this.figuur.toon, px, this.paden[0].kleur,
                             { font: KIDSFONT, gewicht: 700 });
      const vx = this.schrijflijnen.x0 - this.schrijflijnen.k * 0.42;
      if (vx - vb.width / 2 > 8) {
        ctx.globalAlpha = 0.9;
        ctx.drawImage(vb, vx - vb.width / 2, this.H * 0.52 - vb.height / 2);
        ctx.globalAlpha = 1;
      }
    }

    if (duo && this.duoHintT > 2.5 && this.doneT <= 0) {
      this._pulsTekst(ctx, "Gebruik allebei je handen!", nu);
    } else if (nu - this.lastLit > 8 && this.doneT <= 0) {
      this._pulsTekst(ctx, "Volg de stipjes met je wijsvinger!", nu);
    }
    if (this.levelBannerT > 0) this._tekenLevelBanner(ctx);
  }

  _tekenPad(ctx, pad, padIdx, nu, actief = -1) {
    const { dots, lit, progress, kleur } = pad;
    if (!dots.length) return;
    const strokes = this.figuur.strokes;
    // halen die nog niet aan de beurt zijn: vast te zien, maar gedimd
    const dof = strokes && padIdx > actief ? 0.35 : 1;
    ctx.globalAlpha = dof;
    // vage voorbeeldlijn
    ctx.strokeStyle = "rgba(120,124,165,0.55)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    dots.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.stroke();
    ctx.globalAlpha = 1;
    // het al gevolgde stuk, met gloed (twee lagen: breed doorschijnend + strak —
    // véél goedkoper dan shadowBlur, dat elk frame een filter kost)
    if (progress >= 2) {
      ctx.save();
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.beginPath();
      for (let i = 0; i < progress; i++) {
        const [x, y] = dots[i];
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.globalCompositeOperation = "lighter";
      ctx.globalAlpha = 0.30;
      ctx.strokeStyle = kleur;
      ctx.lineWidth = 18;
      ctx.stroke();
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;
      ctx.lineWidth = 7;
      ctx.stroke();
      ctx.restore();
    }
    // afrondings-animatie: een lichtstreep raast over de hele lijn
    if (this.sweepT >= 0 && this.sweepT < 0.9) {
      const kop = this.sweepT / 0.9 * dots.length;
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.lineCap = "round";
      ctx.beginPath();
      for (let i = Math.max(0, Math.floor(kop) - 4); i < Math.min(dots.length, Math.ceil(kop)); i++) {
        const [x, y] = dots[i];
        ctx.lineTo(x, y);
      }
      ctx.globalAlpha = 0.5;
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 22;
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.lineWidth = 9;
      ctx.stroke();
      ctx.restore();
    }
    // stipjes
    ctx.globalAlpha = dof;
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
    ctx.globalAlpha = 1;
    // strokes-figuren met meer halen: cijfertje bij het begin van elke haal,
    // zodat de schrijfvolgorde te zien is zoals in een schrijfschrift
    // (bij woorden telt de nummering per letter; halen van éénhaals-letters
    // krijgen geen cijfertje)
    const nr = this.figuur.badges ? this.figuur.badges[padIdx]
             : strokes && this.paden.length > 1 ? padIdx + 1 : null;
    if (strokes && nr != null) {
      const [bx, by] = dots[0];
      const af = progress >= dots.length;
      const aanBeurt = padIdx === actief;
      ctx.globalAlpha = aanBeurt ? 1 : 0.55;
      ctx.fillStyle = af ? "rgba(23,22,51,0.5)"
                         : aanBeurt ? KLEUREN.AMBER : "rgba(23,22,51,0.85)";
      ctx.beginPath();
      ctx.arc(bx - 24, by - 24, 14, 0, Math.PI * 2);
      ctx.fill();
      const spr = tekstSprite(String(nr), 20,
                              af ? "#8b90b8" : aanBeurt ? "#1a1530" : "#fff",
                              { gewicht: 800, schaduw: false });
      ctx.drawImage(spr, bx - 24 - spr.width / 2, by - 24 - spr.height / 2);
      ctx.globalAlpha = 1;
    }
    // markeer de volgende stip: pulserende ring + draaiend sterretje
    // (bij strokes-figuren alleen op de haal die aan de beurt is)
    if (this.doneT <= 0 && progress < dots.length && (!strokes || padIdx === actief)) {
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
        const w = tekstSprite("wacht op je andere hand…", Math.round(this.H * 0.026),
                              KLEUREN.AMBER, { gewicht: 700, schaduw: false });
        ctx.drawImage(w, x - w.width / 2, y - rr - 12 - w.height / 2);
      }
    }
  }

  // schrijfregel zoals in een schrijfschrift: grondlijn doorgetrokken,
  // x-hoogte gestippeld, bovenlijn heel vaag
  _tekenSchrijfregel(ctx) {
    const { x0, x1, top, xh, grond } = this.schrijflijnen;
    ctx.save();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(140,150,205,0.45)";
    ctx.beginPath();
    ctx.moveTo(x0, grond);
    ctx.lineTo(x1, grond);
    ctx.stroke();
    ctx.setLineDash([10, 10]);
    ctx.strokeStyle = "rgba(140,150,205,0.32)";
    ctx.beginPath();
    ctx.moveTo(x0, xh);
    ctx.lineTo(x1, xh);
    ctx.stroke();
    ctx.strokeStyle = "rgba(140,150,205,0.18)";
    ctx.beginPath();
    ctx.moveTo(x0, top);
    ctx.lineTo(x1, top);
    ctx.stroke();
    ctx.restore();
  }

  _pulsTekst(ctx, tekst, nu) {
    const puls = 0.5 + 0.5 * Math.sin(nu * 2.6);
    const spr = tekstSprite(tekst, Math.round(this.H * 0.045), "#fff");
    ctx.globalAlpha = 0.6 + 0.4 * puls;
    ctx.drawImage(spr, this.W / 2 - spr.width / 2, this.H * 0.88 - spr.height / 2);
    ctx.globalAlpha = 1;
  }

  _tekenLevelBanner(ctx) {
    const k = Math.min(1, (2.0 - this.levelBannerT) / 0.25);
    const alpha = this.levelBannerT > 0.5 ? 1 : this.levelBannerT / 0.5;
    const tekst = this.levelIdx < this.levels.length
      ? (this.figuur.banner ?? `Level ${this.levelIdx + 1}!`)
      : `Alle ${this.levels.length} ${MODI[this.modus].meervoud} gehaald!`;
    const spr = tekstSprite(tekst, Math.round(this.H * 0.09), KLEUREN.AMBER,
                            this.figuur.kader ? { font: KIDSFONT } : {});
    const s = 0.6 + 0.4 * k;
    ctx.globalAlpha = alpha;
    ctx.drawImage(spr, this.W / 2 - spr.width * s / 2, this.H * 0.30 - spr.height * s / 2,
                  spr.width * s, spr.height * s);
    ctx.globalAlpha = 1;
  }
}
