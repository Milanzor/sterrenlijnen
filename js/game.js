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
import { LETTERS, BOVENLIJN } from "./letters.js";
import { WOORDEN } from "./words.js";
import { KLEUREN, SPEELKLEUREN, KIDSFONT, tekenSter, tekstSprite, tekenSprite } from "./fx.js";

const LEAD_MAX = 2;   // duo: zoveel stipjes mag de ene lijn voorlopen
const OPSLAG = "sterrenlijnen";
const MODI = {
  level:  { lijst: LEVELS,  opslag: OPSLAG,              soort: "Level",  meervoud: "levels" },
  letter: { lijst: LETTERS, opslag: `${OPSLAG}-letters`, soort: "Letter", meervoud: "letters" },
  woord:  { lijst: WOORDEN, opslag: `${OPSLAG}-woorden`, soort: "Woord",  meervoud: "woorden" },
};

// kwadraat van de afstand van punt p tot lijnstuk a–b
function afstand2(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay;
  const l2 = dx * dx + dy * dy;
  const t = l2 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2)) : 0;
  return (px - ax - dx * t) ** 2 + (py - ay - dy * t) ** 2;
}

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
  constructor(W, H, fx, geluid, { startLevel = null, modus = "level", bewaren = true } = {}) {
    this.W = W; this.H = H;
    this.fx = fx;
    this.geluid = geluid;
    this.modus = modus;
    this.bewaren = bewaren;  // demostand speelt vanzelf: dat is geen voortgang
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

  resize(W, H) {  // zelfde figuur op de nieuwe maat, mét behoud van wat al getrokken is
    this.W = W; this.H = H;
    const oud = this.paden, { doneT, sweepT } = this;
    this.nieuwFiguur(this.figuur);
    this.doneT = doneT;
    this.sweepT = sweepT;
    this.paden.forEach((p, i) => {
      const o = oud[i], n = p.dots.length;
      p.kleur = o.kleur;
      p.lastLitTime = o.lastLitTime;
      p.progress = o.progress >= o.dots.length ? n
        : Math.min(n - 1, Math.round(o.progress / o.dots.length * n));
      p.lit.fill(true, 0, p.progress);
    });
  }

  get hudSterPos() { return [this.W - 130, 54]; }

  get levelLabel() {
    const n = this.levels.length;
    return this.levelIdx < n ? `${MODI[this.modus].soort} ${this.levelIdx + 1}/${n}`
                             : `${n} ✓ · vrij spelen`;
  }

  bewaar() {
    if (!this.bewaren) return;
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
    // schrijven vraagt precisie: stipjes dichter op elkaar (naar lettermaat)
    // en een kleiner raakvlak, zodat de vinger de lettervorm écht volgt
    const spacing = spec.kader ? k => Math.max(this.H * 0.042, k * 0.16) : this.H * 0.082;
    this.hit = this.H * (spec.kader ? 0.05 : 0.062);
    const { paden: fitted, lijnen, snedes, naarX, naarY, k } =
      fitPaths(spec.paths, this.W, this.H, spacing, spec.kader);
    if (spec.kader) {  // schrijflijnen: bovenlijn (stokhoogte), x-hoogte, grondlijn
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
        top: naarY(BOVENLIJN), xh: naarY(0.5), grond: naarY(1.0), k,
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
      lijn: lijnen[i],   // het échte pad (vloeiend), dots zijn de controlepunten
      na: snedes[i],
      gids: this._lijnPad(lijnen[i], lijnen[i].length),
      spoor: null, spoorN: -1,
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

  _lijnPad(lijn, tot, eind = null) {
    const p = new Path2D();
    for (let q = 0; q < tot; q++) p.lineTo(lijn[q][0], lijn[q][1]);
    if (eind) p.lineTo(eind[0], eind[1]);
    return p;
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
    // Strikt op volgorde: alleen de éérstvolgende stip telt. Stipjes verderop
    // aanraken doet niets — geen voorsprong nemen, geen gaten overslaan. De
    // while laat een snelle vinger binnen één frame wel meerdere stipjes
    // ná elkaar pakken, maar nooit buiten de volgorde om.
    const pad = this.paden[padIdx];
    const ander = this.figuur.duo && this.paden.length > 1 ? this.paden[1 - padIdx] : null;
    const HIT2 = this.hit ** 2;
    while (pad.progress < pad.dots.length) {
      const i = pad.progress;
      const [dx, dy] = pad.dots[i];
      // het hele stukje dat de vinger dit frame aflegde telt, niet alleen
      // het eindpunt: een snelle vinger springt zo nooit over een stip heen
      if (afstand2(dx, dy, v.px, v.py, v.x, v.y) >= HIT2) break;
      if (ander && pad.progress - ander.progress >= LEAD_MAX) {
        // wacht op je andere hand: zachte puls + heel af en toe een tikje
        this.waitPulse[padIdx] = 0.6;
        if (nu - this._lastWaitTik > 1.2) {
          this._lastWaitTik = nu;
          this.geluid.wacht();
        }
        break;
      }
      pad.lit[i] = true;
      pad.litAt[i] = nu;
      pad.lastLitTime = nu;
      this.lastLit = nu;
      pad.progress++;
      this.geluid.pop(this.figuur.duo && padIdx === 1);
      this.fx.gloed(dx, dy, pad.kleur, 4, 0.5);
    }
  }

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
    // schrijfletters hebben lange stokken en staarten: iets kleiner, anders
    // hangen ze in de schrijfregel
    const spr = tekstSprite(naam, Math.round(this.H * (schrijf ? 0.044 : 0.055)), this.paden[0].kleur,
                            schrijf ? { font: KIDSFONT, gewicht: 400 } : {});
    const schaal = this.doneT > 0 ? 1 + Math.sin(Math.min(1, this.sweepT / 0.3) * Math.PI) * 0.18 : 1;
    // de levelbanner neemt even de plek van de naam in (niet over het figuur heen)
    if (this.levelBannerT > 0) this._tekenLevelBanner(ctx);
    else tekenSprite(ctx, spr, this.W / 2, this.H * (schrijf ? 0.13 : 0.15), schaal);

    // voorbeeld naast de schrijfregel, in het kinderfont (Kermit):
    // de losse letter groot, een heel woord wat kleiner
    if (this.figuur.toon) {
      const px = Math.round(this.H * (this.figuur.toon.length > 1 ? 0.11 : 0.22));
      const vb = tekstSprite(this.figuur.toon, px, this.paden[0].kleur,
                             { font: KIDSFONT, gewicht: 400 });
      const vx = this.schrijflijnen.x0 - this.schrijflijnen.k * 0.42;
      if (vx - vb.lw / 2 > 8) {
        ctx.globalAlpha = 0.9;
        tekenSprite(ctx, vb, vx, this.H * 0.52);
        ctx.globalAlpha = 1;
      }
    }

    if (duo && this.duoHintT > 2.5 && this.doneT <= 0) {
      this._pulsTekst(ctx, "Gebruik allebei je handen!", nu);
    } else if (nu - this.lastLit > 8 && this.doneT <= 0) {
      this._pulsTekst(ctx, "Volg de stipjes met je wijsvinger!", nu);
    }
  }

  _tekenPad(ctx, pad, padIdx, nu, actief = -1) {
    const { dots, lit, progress, kleur } = pad;
    if (!dots.length) return;
    const strokes = this.figuur.strokes;
    // halen die nog niet aan de beurt zijn: vast te zien, maar gedimd
    const dof = strokes && padIdx > actief ? 0.35 : 1;
    ctx.globalAlpha = dof;
    // vage voorbeeldlijn: het échte pad, dus letters zijn vloeiend
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.strokeStyle = "rgba(120,124,165,0.55)";
    ctx.lineWidth = 3;
    ctx.stroke(pad.gids);
    ctx.globalAlpha = 1;
    // het al gevolgde stuk, met gloed (twee lagen: breed doorschijnend + strak —
    // véél goedkoper dan shadowBlur, dat elk frame een filter kost)
    if (progress >= 2) {
      if (pad.spoorN !== progress) {  // alleen opnieuw opbouwen bij een nieuwe stip
        const af = progress >= dots.length;
        pad.spoor = this._lijnPad(pad.lijn, af ? pad.lijn.length : pad.na[progress - 1],
                                  af ? null : dots[progress - 1]);
        pad.spoorN = progress;
      }
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.globalAlpha = 0.30;
      ctx.strokeStyle = kleur;
      ctx.lineWidth = 18;
      ctx.stroke(pad.spoor);
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;
      ctx.lineWidth = 7;
      ctx.stroke(pad.spoor);
      ctx.restore();
    }
    // afrondings-animatie: een lichtstreep raast over de hele lijn
    if (this.sweepT >= 0 && this.sweepT < 0.9) {
      const kop = this.sweepT / 0.9 * dots.length;
      const a = Math.max(0, Math.floor(kop) - 4);
      const b = Math.min(dots.length, Math.ceil(kop)) - 1;
      if (b > a) {
        ctx.save();
        ctx.globalCompositeOperation = "lighter";
        ctx.beginPath();
        ctx.moveTo(dots[a][0], dots[a][1]);
        for (let q = pad.na[a]; q < pad.na[b]; q++) ctx.lineTo(pad.lijn[q][0], pad.lijn[q][1]);
        ctx.lineTo(dots[b][0], dots[b][1]);
        ctx.globalAlpha = 0.5;
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 22;
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.lineWidth = 9;
        ctx.stroke();
        ctx.restore();
      }
    }
    // stipjes
    ctx.globalAlpha = dof;
    const r = this.figuur.kader ? 6 : 8;  // schrijven: fijnere stipjes, de lijn is de letter
    for (let i = 0; i < dots.length; i++) {
      const [x, y] = dots[i];
      if (lit[i]) {
        const flits = Math.max(0, 0.35 - (nu - pad.litAt[i])) / 0.35;
        ctx.fillStyle = "#fff";
        ctx.beginPath();
        ctx.arc(x, y, r * 0.85 + flits * 7, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.strokeStyle = "rgba(205,209,238,0.9)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
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
      tekenSprite(ctx, spr, bx - 24, by - 24);
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
        tekenSprite(ctx, w, x, y - rr - 12);
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
    tekenSprite(ctx, spr, this.W / 2, this.H * 0.88);
    ctx.globalAlpha = 1;
  }

  _tekenLevelBanner(ctx) {
    const k = Math.min(1, (2.0 - this.levelBannerT) / 0.25);
    const alpha = this.levelBannerT > 0.5 ? 1 : this.levelBannerT / 0.5;
    const tekst = this.levelIdx < this.levels.length
      ? (this.figuur.banner ?? `Level ${this.levelIdx + 1}!`)
      : `Alle ${this.levels.length} ${MODI[this.modus].meervoud} gehaald!`;
    const spr = tekstSprite(tekst, Math.round(this.H * 0.08), KLEUREN.AMBER,
                            this.figuur.kader ? { font: KIDSFONT, gewicht: 400 } : {});
    const s = 0.6 + 0.4 * k;
    ctx.globalAlpha = alpha;
    tekenSprite(ctx, spr, this.W / 2, this.H * 0.15, s);
    ctx.globalAlpha = 1;
  }
}
