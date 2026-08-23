// Figurenbibliotheek: één-vinger-figuren in zes moeilijkheidslagen (overgezet
// uit de Python-versie) plus twee-handen-figuren: gespiegelde paren die je
// met links en rechts tegelijk natrekt.
//
// Alle figuren zijn doorlopende lijnen in schermcoördinaten (y omlaag).
// Duo-figuren definiëren alleen het rechterpad; het linkerpad is de spiegeling,
// zodat beide handen dezelfde (gespiegelde) beweging maken — dat voelt vanzelf.

function arc(a0, a1, n, cx, cy, rx, ry) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = a0 + (a1 - a0) * i / (n - 1);
    pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
  }
  return pts;
}

function starPoints(n, rIn) {
  const pts = [];
  for (let i = 0; i <= 2 * n; i++) {
    const ang = -Math.PI / 2 + i * Math.PI / n;
    const rr = i % 2 === 0 ? 1.0 : rIn;
    pts.push([Math.cos(ang) * rr, Math.sin(ang) * rr]);
  }
  return pts;
}

const TAU = Math.PI * 2;

function buildSingles() {
  const star5 = [];
  for (let i = 0; i < 5; i++) {
    const a = -Math.PI / 2 + i * TAU / 5;
    star5.push([Math.cos(a), Math.sin(a)]);
  }
  const heart = [];
  for (let i = 0; i <= 60; i++) {
    const t = TAU * i / 60;
    heart.push([16 * Math.sin(t) ** 3,
                -(13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t))]);
  }
  const maan = arc(0.890, TAU - 0.890, 44, 0.5, 0.5, 0.5, 0.5)
    .concat(arc(-1.332, 1.332 - TAU, 28, 0.72, 0.5, 0.40, 0.40));
  const wolk = [[1, 0.72], [0, 0.72]]
    .concat(arc(Math.PI, 0, 16, 0.16, 0.72, 0.16, -0.14))
    .concat(arc(Math.PI, 0, 20, 0.50, 0.72, 0.18, -0.24))
    .concat(arc(Math.PI, 0, 16, 0.84, 0.72, 0.16, -0.14));
  const vis = arc(Math.PI, 0, 26, 0.4, 0.5, 0.4, -0.28)
    .concat([[1.0, 0.30], [1.0, 0.70], [0.8, 0.5]])
    .concat(arc(0, Math.PI, 26, 0.4, 0.5, 0.4, 0.28));
  const bloem = [];
  for (let i = 0; i <= 120; i++) {
    const r = 0.82 + 0.18 * Math.sin(6 * TAU * i / 120);
    bloem.push([r * Math.cos(TAU * i / 120), r * Math.sin(TAU * i / 120)]);
  }
  const slak = [];
  for (let i = 0; i <= 150; i++) {
    const r = 0.15 + 0.85 * i / 150;
    slak.push([r * Math.cos(2.5 * TAU * i / 150), r * Math.sin(2.5 * TAU * i / 150)]);
  }
  const golf = [];
  for (let i = 0; i <= 48; i++) golf.push([i / 48, 0.30 * Math.sin(i / 48 * TAU * 1.5)]);
  const acht = [];
  for (let i = 0; i <= 60; i++) {
    acht.push([0.5 + 0.5 * Math.cos(TAU * i / 60), 0.5 + 0.28 * Math.sin(2 * TAU * i / 60)]);
  }
  return [
    [ // laag 1: losse halen
      ["lijn", [[0, 0], [1, 0]]],
      ["regenboog", arc(Math.PI, 0, 48, 0.5, 0, 0.5, -0.62)],
      ["golf", golf],
      ["berg", [[0, 1], [0.25, 0], [0.5, 1], [0.75, 0], [1, 1]]],
    ],
    [ // laag 2: gesloten basisvormen
      ["vierkant", [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
      ["driehoek", [[0, 1], [0.5, 0], [1, 1], [0, 1]]],
      ["cirkel", arc(-Math.PI / 2, TAU - Math.PI / 2, 60, 0.5, 0.5, 0.5, 0.5)],
      ["vlieger", [[0.5, 0], [0.85, 0.5], [0.5, 1], [0.15, 0.5], [0.5, 0]]],
    ],
    [ // laag 3: herkenbare plaatjes
      ["maan", maan],
      ["huisje", [[0, 1], [0, 0.4], [0.5, 0], [1, 0.4], [1, 1], [0, 1]]],
      ["ster", [0, 2, 4, 1, 3, 0].map(i => star5[i])],
      ["bliksem", [[0.65, 0], [0.25, 0.5], [0.55, 0.5], [0.15, 1]]],
    ],
    [ // laag 4
      ["hart", heart],
      ["kroon", [[0, 1], [0, 0.35], [0.25, 0.65], [0.5, 0.25], [0.75, 0.65], [1, 0.35], [1, 1], [0, 1]]],
      ["raket", [[0.35, 1], [0.35, 0.35], [0.5, 0], [0.65, 0.35], [0.65, 1], [0.35, 1]]],
      ["ijsje", [[0.30, 0.45], [0.5, 1], [0.70, 0.45], [0.78, 0.45]]
        .concat(arc(0, Math.PI, 24, 0.5, 0.45, 0.28, -0.34)).concat([[0.30, 0.45]])],
    ],
    [ // laag 5
      ["wolk", wolk],
      ["acht", acht],
      ["vis", vis],
      ["bloem", bloem],
    ],
    [ // laag 6: lange halen
      ["slak", slak],
      ["zon", starPoints(8, 0.62)],
    ],
  ];
}

// Duo-figuren: rechterpad in eenheden rond x=0; links = spiegeling.
// Allebei beginnen ze in (of bij) het midden, zodat de handen samen naar
// buiten bewegen — spiegelbeweging is voor kinderen de natuurlijkste vorm
// van "twee dingen tegelijk".
function buildDuos() {
  // hart in twee halen: van het kuiltje bovenin allebei rond, samen naar de punt
  const hartR = [];
  for (let i = 0; i <= 30; i++) {
    const t = Math.PI * i / 30;
    hartR.push([16 * Math.sin(t) ** 3,
                -(13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t))]);
  }
  // vlinder: vleugel als lus die bij het lijfje begint en eindigt
  const vleugel = arc(Math.PI * 0.86, -Math.PI * 0.94, 40, 0.62, -0.05, 0.55, 0.62);
  // ballon: rondje + touwtje eronder
  const ballon = arc(-Math.PI / 2, TAU - Math.PI / 2, 36, 0.52, -0.30, 0.30, 0.34)
    .concat([[0.52, 0.04], [0.46, 0.30], [0.54, 0.55]]);
  // bril: rond glas, start aan de binnenkant (bij je neus)
  const glas = arc(Math.PI, Math.PI + TAU, 40, 0.52, 0, 0.34, 0.40);
  return [
    // volgorde = oplopende moeilijkheid
    ["bergen", 1, [[0.04, 0.55], [0.5, -0.55], [0.96, 0.55]]],
    ["regenboog", 1, arc(-Math.PI / 2, 0, 30, 0.02, 0.45, 0.95, -1.0)],
    ["bril", 2, glas],
    ["ballonnen", 2, ballon],
    ["hart", 3, hartR],
    ["vlinder", 3, vleugel],
  ];
}

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

// Past één of twee paden samen in een kader op het scherm (verhoudingen intact).
export function fitPaths(rawPaths, W, H, spacing) {
  let xs = [], ys = [];
  for (const p of rawPaths) for (const [x, y] of p) { xs.push(x); ys.push(y); }
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const w = (maxX - minX) || 1, h = (maxY - minY) || 1;
  const k = Math.min(W * 0.66 / w, H * 0.52 / h);
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  return rawPaths.map(p => resample(
    p.map(([x, y]) => [(x - cx) * k + W / 2, (y - cy) * k + H * 0.55]), spacing));
}

const SINGLES = buildSingles();
const DUOS = buildDuos();

// De wachtrij: eerst laag voor laag (geschud per laag), met vanaf laag 2 na
// elke twee figuren een duo-figuur ertussen; daarna alles door elkaar.
export function makeQueue(rng = Math.random) {
  const shuffled = arr => {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };
  const queue = [];
  const duoByTier = [DUOS.filter(d => d[1] === 1), DUOS.filter(d => d[1] === 2),
                     DUOS.filter(d => d[1] === 3)];
  let duoTier = 0, duoIdx = 0, sinceDuo = 0;
  SINGLES.forEach((tier, ti) => {
    for (const [name, pts] of shuffled(tier)) {
      queue.push({ name, paths: [pts], duo: false });
      sinceDuo++;
      if (ti >= 1 && sinceDuo >= 2) {
        const pool = duoByTier[Math.min(duoTier, 2)];
        if (pool.length) {
          const [dName, , right] = pool[duoIdx % pool.length];
          queue.push({ name: dName, paths: duoPaths(right), duo: true });
          duoIdx++;
          if (duoIdx % pool.length === 0) duoTier++;
          sinceDuo = 0;
        }
      }
    }
  });
  return queue;
}

export function refillQueue(rng = Math.random) {
  // alles door elkaar: singles en duo's gemengd
  const all = [];
  for (const tier of SINGLES) for (const [name, pts] of tier) {
    all.push({ name, paths: [pts], duo: false });
  }
  for (const [name, , right] of DUOS) all.push({ name, paths: duoPaths(right), duo: true });
  for (let i = all.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [all[i], all[j]] = [all[j], all[i]];
  }
  return all;
}

function duoPaths(right) {
  const left = right.map(([x, y]) => [-x, y]);
  return [left, right];  // pad 0 = links, pad 1 = rechts
}
