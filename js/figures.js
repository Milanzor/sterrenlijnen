// Levelbibliotheek: 100 unieke figuren, oplopend in moeilijkheid.
//
// Enkelfiguren zijn één doorlopende lijn (kruisen mag, terugtekenen niet) in
// schermcoördinaten (y omlaag). Duo-figuren definiëren alleen het rechterpad;
// het linkerpad is de spiegeling, zodat beide handen dezelfde (gespiegelde)
// beweging maken — dat voelt vanzelf. Cijfers zitten er ook tussen: spelend
// leren schrijven.

const TAU = Math.PI * 2;

function arc(a0, a1, n, cx, cy, rx, ry) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = a0 + (a1 - a0) * i / (n - 1);
    pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
  }
  return pts;
}

function poly(n, r = 1) {  // regelmatige veelhoek, punt boven, gesloten
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const a = -Math.PI / 2 + i * TAU / n;
    pts.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  return pts;
}

function ster(n, rIn) {  // n-puntige ster, gesloten
  const pts = [];
  for (let i = 0; i <= 2 * n; i++) {
    const a = -Math.PI / 2 + i * Math.PI / n;
    const rr = i % 2 === 0 ? 1 : rIn;
    pts.push([Math.cos(a) * rr, Math.sin(a) * rr]);
  }
  return pts;
}

function param(n, fn) {  // fn(t) → [x, y], t in 0..1
  const pts = [];
  for (let i = 0; i <= n; i++) pts.push(fn(i / n));
  return pts;
}

function roos(bladen, n = 220) {  // rozetkromme r = cos(k·θ): propeller/klavertje
  const k = bladen === 3 ? 1.5 : 2;
  const omw = bladen === 3 ? 2 : 1;
  return param(n, t => {
    const th = TAU * omw * t;
    const r = Math.cos(k * th);
    return [r * Math.cos(th), r * Math.sin(th)];
  });
}

function hartPts(van = 0, tot = 1, n = 60) {  // van/tot in halve omlopen
  return param(n, u => {
    const t = Math.PI * (van + (tot - van) * u);
    return [16 * Math.sin(t) ** 3,
            -(13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t))];
  });
}

function kidSter() {  // vijfpuntster in één haal, zoals kinderen hem tekenen
  const p = [];
  for (const i of [0, 2, 4, 1, 3, 0]) {
    const a = -Math.PI / 2 + i * TAU / 5;
    p.push([Math.cos(a), Math.sin(a)]);
  }
  return p;
}

function acht(rx = 0.5, ry = 0.28) {
  return param(72, t => [rx * Math.cos(TAU * t), ry * Math.sin(2 * TAU * t)]);
}

function golf(periodes, amp, n = 60) {
  return param(n, t => [t, amp * Math.sin(TAU * periodes * t)]);
}

function lus(cx, hoogte, lussen = 1) {  // cycloïde: lijn met loopings erin
  return param(60 * lussen, t => [t - cx * Math.sin(TAU * lussen * t),
                                  -hoogte * (1 - Math.cos(TAU * lussen * t))]);
}

// ---------------------------------------------------------------- figuren

function S(name, moeilijk, pts) { return { name, moeilijk, duo: false, paths: [pts] }; }
function D(name, moeilijk, rechts) {
  return { name, moeilijk, duo: true,
           paths: [rechts.map(([x, y]) => [-x, y]), rechts] };
}

function bouwLevels() {
  const F = [];

  // ---- laag 1-2: losse halen en simpele vormen ----
  F.push(S("lijn", 1, [[0, 0], [1, 0]]));
  F.push(S("glijbaan", 1, [[0, 0], [0.18, 0.04], [0.42, 0.3], [0.62, 0.68], [0.82, 0.88], [1, 0.92]]));
  F.push(S("hoekje", 1, [[0, 0], [0, 1], [1, 1]]));
  F.push(S("vinkje", 1, [[0, 0.55], [0.35, 1], [1, 0]]));
  F.push(S("regenboog", 1, arc(Math.PI, 0, 48, 0.5, 0, 0.5, -0.62)));
  F.push(S("berg", 1, [[0, 1], [0.25, 0], [0.5, 1], [0.75, 0], [1, 1]]));
  F.push(S("golf", 1, golf(1.5, 0.3)));
  F.push(S("grote golf", 2, golf(1, 0.5, 40)));
  F.push(S("poort", 2, [[0, 1], [0, 0.5], ...arc(Math.PI, 0, 24, 0.5, 0.5, 0.5, -0.5), [1, 1]]));
  F.push(S("trap", 2, [[0, 1], [0, 0.66], [0.33, 0.66], [0.33, 0.33], [0.66, 0.33], [0.66, 0], [1, 0]]));
  F.push(S("zigzag", 2, [[0, 1], [0.2, 0], [0.4, 1], [0.6, 0], [0.8, 1], [1, 0]]));
  F.push(S("zee", 2, [...arc(Math.PI, 0, 14, 0.17, 0.5, 0.17, -0.3),
                      ...arc(Math.PI, 0, 14, 0.5, 0.5, 0.17, -0.3),
                      ...arc(Math.PI, 0, 14, 0.83, 0.5, 0.17, -0.3)]));
  F.push(S("hartslag", 2, [[0, 0.5], [0.28, 0.5], [0.38, 0.1], [0.5, 0.9], [0.6, 0.5], [1, 0.5]]));
  F.push(S("slang", 2, param(60, t => [0.5 + 0.4 * Math.sin(3 * Math.PI * t), t])));

  // ---- laag 2-3: gesloten basisvormen ----
  F.push(S("vierkant", 2, [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]));
  F.push(S("driehoek", 2, [[0, 1], [0.5, 0], [1, 1], [0, 1]]));
  F.push(S("cirkel", 2, arc(-Math.PI / 2, TAU - Math.PI / 2, 60, 0.5, 0.5, 0.5, 0.5)));
  F.push(S("ruit", 2, [[0.5, 0], [1, 0.5], [0.5, 1], [0, 0.5], [0.5, 0]]));
  F.push(S("deur", 2, [[0, 1], [0, 0], [0.6, 0], [0.6, 1], [0, 1]]));
  F.push(S("ei", 2, arc(-Math.PI / 2, TAU - Math.PI / 2, 44, 0.5, 0.5, 0.38, 0.5)));
  F.push(S("vlieger", 3, [[0.5, 0], [0.85, 0.5], [0.5, 1], [0.15, 0.5], [0.5, 0]]));
  F.push(S("druppel", 3, [[0.5, 0], ...arc(-Math.PI * 0.3, Math.PI * 1.3, 30, 0.5, 0.62, 0.34, 0.34), [0.5, 0]]));
  F.push(S("vijfhoek", 3, poly(5)));
  F.push(S("zeshoek", 3, poly(6)));
  F.push(S("stopbord", 3, poly(8)));
  F.push(S("zandloper", 3, [[0, 0], [1, 0], [0, 1], [1, 1], [0, 0]]));
  F.push(S("edelsteen", 3, [[0.2, 0], [0.8, 0], [1, 0.35], [0.5, 1], [0, 0.35], [0.2, 0]]));

  // ---- laag 3-4: herkenbare plaatjes ----
  F.push(S("maan", 3, [...arc(0.890, TAU - 0.890, 44, 0.5, 0.5, 0.5, 0.5),
                       ...arc(-1.332, 1.332 - TAU, 28, 0.72, 0.5, 0.40, 0.40)]));
  F.push(S("huisje", 3, [[0, 1], [0, 0.4], [0.5, 0], [1, 0.4], [1, 1], [0, 1]]));
  F.push(S("ster", 3, kidSter()));
  F.push(S("bliksem", 3, [[0.65, 0], [0.25, 0.5], [0.55, 0.5], [0.15, 1]]));
  F.push(S("vonkje", 3, ster(4, 0.4)));
  F.push(S("bootje", 3, [[0, 0.35], [0.25, 0.85], [0.75, 0.85], [1, 0.35], [0, 0.35]]));
  F.push(S("vlag", 3, [[0.25, 1], [0.25, 0.05], [0.95, 0.2], [0.25, 0.4]]));
  F.push(S("vogeltje", 3, [...arc(Math.PI, Math.PI * 1.85, 16, 0.28, 0.6, 0.26, 0.34),
                           ...arc(Math.PI * 1.15, Math.PI * 2, 16, 0.74, 0.6, 0.26, 0.34)]));
  F.push(S("hoedje", 3, [[0, 0.7], [0.25, 0.7], [0.3, 0.25], [0.7, 0.25], [0.75, 0.7], [1, 0.7]]));
  F.push(S("lolly", 4, [...arc(Math.PI / 2, Math.PI / 2 + TAU, 36, 0.5, 0.28, 0.28, 0.28),
                        [0.5, 0.56], [0.5, 1]]));
  F.push(S("banaan", 4, [...arc(Math.PI * 1.1, Math.PI * 1.9, 26, 0.5, 0.85, 0.5, 0.62),
                         ...arc(Math.PI * 1.9, Math.PI * 1.1, 26, 0.5, 0.98, 0.42, 0.55)]));
  F.push(S("pizza", 4, [[0.5, 1], [0.12, 0.25], ...arc(Math.PI, 0, 20, 0.5, 0.25, 0.38, -0.18),
                        [0.88, 0.25], [0.5, 1]]));
  F.push(S("kaars", 4, [[0.4, 1], [0.4, 0.35], [0.45, 0.2], [0.5, 0.04], [0.55, 0.2],
                        [0.6, 0.35], [0.6, 1], [0.4, 1]]));
  F.push(S("tol", 4, [[0.15, 0.35], [0.5, 1], [0.85, 0.35],
                      ...arc(0, -Math.PI, 20, 0.5, 0.35, 0.35, 0.28)]));
  F.push(S("wortel", 4, [[0.35, 0.15], [0.5, 1], [0.65, 0.15], [0.58, 0.02], [0.52, 0.15],
                         [0.46, 0.0], [0.4, 0.13], [0.35, 0.15]]));
  F.push(S("appel", 4, [...arc(-Math.PI * 0.38, Math.PI * 1.38, 40, 0.5, 0.58, 0.4, 0.4),
                        [0.5, 0.14], [0.58, 0.0]]));
  F.push(S("peer", 4, [[0.5, 0.05], [0.62, 0.25], [0.72, 0.5], [0.68, 0.8], [0.5, 0.95],
                       [0.32, 0.8], [0.28, 0.5], [0.38, 0.25], [0.5, 0.05]]));
  F.push(S("envelop", 4, [[0, 0], [0.5, 0.45], [1, 0], [1, 0.7], [0, 0.7], [0, 0]]));
  F.push(S("papieren vliegtuigje", 4, [[0, 0.35], [1, 0.05], [0.4, 0.6], [0, 0.35],
                                       [0.4, 0.6], [0.5, 0.95]]));

  // ---- cijfers: spelend leren schrijven ----
  F.push(S("cijfer 1", 2, [[0.35, 0.25], [0.55, 0.05], [0.55, 0.95]]));
  F.push(S("cijfer 7", 2, [[0.2, 0.08], [0.8, 0.08], [0.42, 0.95]]));
  F.push(S("cijfer 2", 3, [...arc(Math.PI * 0.95, -Math.PI * 0.1, 18, 0.48, 0.28, 0.3, 0.24),
                           [0.2, 0.95], [0.8, 0.95]]));
  F.push(S("cijfer 3", 4, [...arc(-Math.PI * 0.6, Math.PI * 0.5, 16, 0.45, 0.27, 0.28, 0.24),
                           ...arc(-Math.PI * 0.5, Math.PI * 0.6, 16, 0.45, 0.72, 0.31, 0.26)]));
  F.push(S("cijfer 5", 4, [[0.75, 0.05], [0.3, 0.05], [0.28, 0.42],
                           ...arc(-Math.PI * 0.5, Math.PI * 0.62, 18, 0.47, 0.68, 0.3, 0.28)]));
  F.push(S("cijfer 6", 5, [[0.72, 0.06], [0.52, 0.2], [0.35, 0.46],
                           ...arc(-Math.PI * 0.75, Math.PI * 1.25, 32, 0.48, 0.68, 0.27, 0.27)]));
  F.push(S("cijfer 9", 5, [...arc(-Math.PI * 0.25, -Math.PI * 0.25 + TAU, 32, 0.48, 0.32, 0.26, 0.27),
                           [0.68, 0.6], [0.58, 0.95]]));

  // ---- laag 4-5: bekende toppers en nieuwe plaatjes ----
  F.push(S("hart", 4, hartPts(0, 2)));
  F.push(S("kroon", 4, [[0, 1], [0, 0.35], [0.25, 0.65], [0.5, 0.25], [0.75, 0.65],
                        [1, 0.35], [1, 1], [0, 1]]));
  F.push(S("raket", 4, [[0.35, 1], [0.35, 0.35], [0.5, 0], [0.65, 0.35], [0.65, 1], [0.35, 1]]));
  F.push(S("ijsje", 4, [[0.30, 0.45], [0.5, 1], [0.70, 0.45], [0.78, 0.45],
                        ...arc(0, Math.PI, 24, 0.5, 0.45, 0.28, -0.34), [0.30, 0.45]]));
  F.push(S("paddenstoel", 5, [[0.15, 0.5], ...arc(Math.PI, 0, 24, 0.5, 0.5, 0.35, -0.45),
                              [0.85, 0.5], [0.62, 0.5], [0.62, 0.95], [0.38, 0.95],
                              [0.38, 0.5], [0.15, 0.5]]));
  F.push(S("kopje", 5, [[0.15, 0.2], [0.2, 0.85], [0.8, 0.85], [0.85, 0.55],
                        ...arc(Math.PI * 0.5, -Math.PI * 0.5, 14, 0.87, 0.42, 0.13, 0.13),
                        [0.85, 0.28], [0.85, 0.2]]));
  F.push(S("kasteel", 5, [[0, 1], [0, 0.35], [0.2, 0.35], [0.2, 0.15], [0.4, 0.15], [0.4, 0.35],
                          [0.6, 0.35], [0.6, 0.15], [0.8, 0.15], [0.8, 0.35], [1, 0.35],
                          [1, 1], [0, 1]]));
  F.push(S("ufo", 5, param(64, t => {
    const a = TAU * t;
    let y = 0.55 + 0.18 * Math.sin(a);
    if (Math.sin(a) < -0.3) y -= 0.3 * (-Math.sin(a) - 0.3);
    return [0.5 + 0.5 * Math.cos(a), y];
  })));
  F.push(S("sleutel", 5, [...arc(0, TAU, 26, 0.25, 0.3, 0.18, 0.18), [0.43, 0.3], [0.95, 0.3],
                          [0.95, 0.5], [0.87, 0.5], [0.87, 0.38], [0.78, 0.38], [0.78, 0.5]]));
  F.push(S("wolk", 5, [[1, 0.72], [0, 0.72],
                       ...arc(Math.PI, 0, 16, 0.16, 0.72, 0.16, -0.14),
                       ...arc(Math.PI, 0, 20, 0.50, 0.72, 0.18, -0.24),
                       ...arc(Math.PI, 0, 16, 0.84, 0.72, 0.16, -0.14)]));
  F.push(S("gebergte", 5, [[0, 1], [0.14, 0.2], [0.28, 0.75], [0.42, 0.05], [0.58, 0.75],
                           [0.72, 0.12], [0.86, 0.7], [1, 1]]));
  F.push(S("vlieger met staart", 5, [[0.5, 0.6], [0.2, 0.3], [0.5, 0], [0.8, 0.3], [0.5, 0.6],
                                     [0.56, 0.72], [0.44, 0.84], [0.56, 0.96]]));
  F.push(S("sneeuwster", 5, ster(6, 0.5)));
  F.push(S("toverstaf", 5, (() => {
    const p = [];
    for (const i of [2, 4, 1, 3, 0, 2]) {
      const a = -Math.PI / 2 + i * TAU / 5;
      p.push([0.35 + 0.3 * Math.cos(a), 0.3 + 0.3 * Math.sin(a)]);
    }
    p.push([0.9, 1.0]);
    return p;
  })()));

  // ---- laag 6-8: lussen, krommen en lange halen ----
  F.push(S("acht", 6, acht()));
  F.push(S("sneeuwpop", 6, param(80, t => {
    const a = TAU * t;
    const s = 0.16 + 0.15 * (1 - Math.cos(a)) / 2;  // onderbol groter dan de kop
    return [0.5 + s * Math.sin(2 * a) * 2.2, 0.5 - 0.5 * Math.cos(a)];
  })));
  F.push(S("lusje", 6, lus(0.3, 0.3)));
  F.push(S("krul", 6, param(80, t => {
    const r = 0.15 + 0.85 * t;
    return [r * Math.cos(1.6 * TAU * t), r * Math.sin(1.6 * TAU * t)];
  })));
  F.push(S("vis", 6, [...arc(Math.PI, 0, 26, 0.4, 0.5, 0.4, -0.28),
                      [1.0, 0.30], [1.0, 0.70], [0.8, 0.5],
                      ...arc(0, Math.PI, 26, 0.4, 0.5, 0.4, 0.28)]));
  F.push(S("bloem", 6, param(120, t => {
    const r = 0.82 + 0.18 * Math.sin(6 * TAU * t);
    return [r * Math.cos(TAU * t), r * Math.sin(TAU * t)];
  })));
  F.push(S("madeliefje", 7, param(160, t => {
    const r = 0.78 + 0.22 * Math.sin(8 * TAU * t);
    return [r * Math.cos(TAU * t), r * Math.sin(TAU * t)];
  })));
  F.push(S("springveer", 7, lus(0.09, 0.2, 3)));
  F.push(S("klavertje vier", 7, roos(4)));
  F.push(S("propeller", 7, roos(3)));
  F.push(S("achtbaan", 8, [[0, 0.78], [0.2, 0.74],
                           ...lus(0.28, 0.32).map(([x, y]) => [0.2 + 0.6 * x, 0.74 + y]),
                           [1, 0.66]]));
  F.push(S("slak", 8, param(150, t => {
    const r = 0.15 + 0.85 * t;
    return [r * Math.cos(2.5 * TAU * t), r * Math.sin(2.5 * TAU * t)];
  })));
  F.push(S("zon", 8, ster(8, 0.62)));

  // ---- duo's: twee handen tegelijk (gespiegeld, samen naar buiten) ----
  F.push(D("bergen", 3, [[0.04, 0.55], [0.5, -0.55], [0.96, 0.55]]));
  F.push(D("dubbele regenboog", 3, arc(-Math.PI / 2, 0, 30, 0.02, 0.45, 0.95, -1.0)));
  F.push(D("golven", 4, param(50, t => [0.02 + 0.95 * t, 0.3 * Math.sin(TAU * 1.25 * t)])));
  F.push(D("bril", 4, arc(Math.PI, Math.PI + TAU, 40, 0.52, 0, 0.34, 0.40)));
  F.push(D("ballonnen", 5, [...arc(-Math.PI / 2, TAU - Math.PI / 2, 36, 0.52, -0.30, 0.30, 0.34),
                            [0.52, 0.04], [0.46, 0.30], [0.54, 0.55]]));
  F.push(D("kersen", 5, [[0.02, -0.55], [0.4, 0.14],
                         ...arc(-Math.PI / 2, -Math.PI / 2 + TAU, 30, 0.4, 0.46, 0.3, 0.32)]));
  F.push(D("wolkjes", 5, [[0.95, 0.25], [0.2, 0.25],
                          ...arc(Math.PI, 0, 12, 0.32, 0.25, 0.12, -0.12),
                          ...arc(Math.PI, 0, 14, 0.58, 0.25, 0.14, -0.18),
                          ...arc(Math.PI, 0, 12, 0.83, 0.25, 0.12, -0.12)]));
  F.push(D("bliksems", 6, [[0.15, -0.6], [0.45, -0.1], [0.25, -0.1], [0.6, 0.6]]));
  F.push(D("torens", 6, [[0.15, 1], [0.15, -0.2], [0.05, -0.2], [0.35, -0.55],
                         [0.65, -0.2], [0.55, -0.2], [0.55, 1]]));
  F.push(D("grote brug", 6, [...arc(-Math.PI / 2, -Math.PI * 0.06, 20, 0.02, 0.55, 0.9, 1.0),
                             [0.93, 0.75]]));
  F.push(D("tulp", 7, [[0.02, 1.0], [0.02, 0.3], [0.45, 0.42], [0.55, -0.05],
                       [0.30, -0.25], [0.02, -0.05]]));
  F.push(D("kerstboom", 7, [[0.02, -1.0], [0.5, -0.45], [0.25, -0.45], [0.75, 0.1],
                            [0.42, 0.1], [0.95, 0.7], [0.12, 0.7], [0.12, 1.0]]));
  F.push(D("strik", 7, [[0.03, 0.0], [0.6, -0.5], [0.95, -0.2], [0.9, 0.25],
                        [0.55, 0.45], [0.03, 0.0]]));
  F.push(D("vleermuis", 8, [[0.05, -0.1], [0.5, -0.45], [0.95, -0.15], [0.8, 0.15],
                            [0.6, 0.05], [0.45, 0.3], [0.2, 0.2], [0.05, 0.35]]));
  F.push(D("twee hartjes", 8, hartPts(0, 2, 40).map(([x, y]) => [0.55 + x * 0.028, y * 0.028])));
  F.push(D("groot hart", 8, hartPts(0, 1, 30)));
  F.push(D("vlinder", 9, arc(Math.PI * 0.86, -Math.PI * 0.94, 40, 0.62, -0.05, 0.55, 0.62)));
  F.push(D("krulletjes", 9, param(80, t => {
    const r = 0.1 + 0.9 * t;
    return [0.5 + 0.45 * r * Math.cos(2.2 * TAU * t), 0.45 * r * Math.sin(2.2 * TAU * t)];
  })));
  F.push(D("dubbele acht", 10, acht(0.4, 0.5).map(([x, y]) => [0.55 + x, y])));
  F.push(D("dubbele ster", 10, kidSter().map(([x, y]) => [0.58 + x * 0.5, y * 0.5])));

  // sorteer op moeilijkheid (stabiel: binnen een moeilijkheid blijft de
  // schrijfvolgorde), en vlecht de duo's er gelijkmatig doorheen: het eerste
  // duo rond level 10, de twee zwaarste als grote finale op 99 en 100
  const singles = F.filter(f => !f.duo).sort((a, b) => a.moeilijk - b.moeilijk);
  const duos = F.filter(f => f.duo).sort((a, b) => a.moeilijk - b.moeilijk);
  const totaal = singles.length + duos.length;
  const duoPlekken = new Set(duos.map((_, i) =>
    Math.round(10 + i * (totaal - 10) / (duos.length - 1))));
  const levels = [];
  for (let lvl = 1; lvl <= totaal; lvl++) {
    const bron = (duoPlekken.has(lvl) && duos.length) || !singles.length ? duos : singles;
    levels.push(bron.shift());
  }
  return levels;
}

export const LEVELS = bouwLevels();

export function resample(pts, spacing) {
  const out = [pts[0].slice()];
  let acc = 0;
  let [x0, y0] = pts[0];
  for (let i = 1; i < pts.length; i++) {
    let [x1, y1] = pts[i];
    let seg = Math.hypot(x1 - x0, y1 - y0);
    while (seg > 0 && acc + seg >= spacing) {
      const t = (spacing - acc) / seg;
      x0 += (x1 - x0) * t;
      y0 += (y1 - y0) * t;
      seg = Math.hypot(x1 - x0, y1 - y0);
      acc = 0;
      out.push([x0, y0]);
    }
    acc += seg;
    x0 = x1; y0 = y1;
  }
  return out;
}

// Past de paden samen in een kader op het scherm (verhoudingen intact).
// Optioneel `kader` legt de verticale maat vast (letters: vaste schrijflijnen,
// zodat een c niet even groot wordt als een k). Geeft naast de paden ook de
// transformatie terug, zodat de schrijflijnen meegetekend kunnen worden.
export function fitPaths(rawPaths, W, H, spacing, kader = null) {
  let xs = [], ys = [];
  for (const p of rawPaths) for (const [x, y] of p) { xs.push(x); ys.push(y); }
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = kader ? kader.minY : Math.min(...ys);
  const maxY = kader ? kader.maxY : Math.max(...ys);
  const w = (maxX - minX) || 1, h = (maxY - minY) || 1;
  // letters (vast kader) mogen wat groter: hun kader bevat al witruimte
  const k = Math.min(W * 0.66 / w, H * (kader ? 0.62 : 0.52) / h);
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  const naarX = x => (x - cx) * k + W / 2;
  const naarY = y => (y - cy) * k + H * 0.55;
  return { paden: rawPaths.map(p => resample(
             p.map(([x, y]) => [naarX(x), naarY(y)]), spacing)),
           naarX, naarY, k };
}
