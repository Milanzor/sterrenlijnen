// Letterbibliotheek voor de Letter leer modus: alle 26 kleine drukletters
// (blokschrift), elk als één of meer halen in de échte schrijfvolgorde en
// -richting — zoals kinderen ze op school leren schrijven. De halen worden
// ná elkaar getrokken (strokes-figuren in game.js), met een cijfertje bij
// het begin van elke haal.
//
// Coördinaten: y omlaag, vaste schrijflijnen voor álle letters zodat ze in
// verhouding blijven: bovenlijn 0.1 (stokletters), x-hoogte 0.5,
// grondlijn 1.0, staartlijn ~1.35 (staartletters).

const TAU = Math.PI * 2;

function arc(a0, a1, n, cx, cy, rx, ry) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = a0 + (a1 - a0) * i / (n - 1);
    pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
  }
  return pts;
}

// het rondje van a/d/g/o/q: linksom (tegen de klok in), zoals je het schrijft
const rondje = (a0 = -0.25 * Math.PI) => arc(a0, a0 - TAU, 36, 0.4, 0.75, 0.25, 0.25);
// het puntje op de i en de j: een mini-rondje
const stip = (x, y) => arc(-Math.PI / 2, -Math.PI / 2 - TAU, 8, x, y, 0.05, 0.05);
// het boogje van n/m/h: vanaf de stok omhoog en over de heuvel naar rechts
const boog = (cx, rx) => arc(Math.PI, 0, 14, cx, 0.72, rx, -0.22);

// vaste verticale maat (schrijflijnen) — ook gebruikt door de Woorden modus
export const KADER = { minY: 0.02, maxY: 1.43 };

function L(letter, ...paths) {
  return { name: `de letter ${letter}`, letter, toon: letter, strokes: true,
           duo: false, paths, kader: KADER, banner: `de ${letter}!`,
           zegNieuw: `de letter ${letter}`, zegKlaar: letter,
           badges: paths.length > 1 ? paths.map((_, i) => i + 1) : null };
}

export const LETTERS = [
  L("a", rondje(), [[0.65, 0.5], [0.65, 1.0]]),
  L("b", [[0.15, 0.1], [0.15, 1.0]],
         arc(-Math.PI / 2, Math.PI / 2, 18, 0.15, 0.75, 0.38, 0.25)),
  L("c", arc(-0.35 * Math.PI, -1.65 * Math.PI, 30, 0.42, 0.75, 0.26, 0.26)),
  L("d", rondje(), [[0.65, 0.1], [0.65, 1.0]]),
  L("e", [[0.16, 0.75], [0.65, 0.75], ...arc(0, -1.7 * Math.PI, 30, 0.4, 0.75, 0.25, 0.25)]),
  L("f", [...arc(-0.15 * Math.PI, -Math.PI, 14, 0.45, 0.3, 0.22, 0.2), [0.23, 1.0]],
         [[0.08, 0.5], [0.45, 0.5]]),
  L("g", rondje(), [[0.65, 0.5], [0.65, 1.08], ...arc(0, 0.92 * Math.PI, 12, 0.42, 1.08, 0.23, 0.27)]),
  L("h", [[0.15, 0.1], [0.15, 1.0]], [...boog(0.4, 0.25), [0.65, 1.0]]),
  L("i", [[0.3, 0.5], [0.3, 1.0]], stip(0.3, 0.3)),
  L("j", [[0.42, 0.5], [0.42, 1.08], ...arc(0, 0.92 * Math.PI, 12, 0.19, 1.08, 0.23, 0.27)],
         stip(0.42, 0.3)),
  L("k", [[0.15, 0.1], [0.15, 1.0]], [[0.55, 0.5], [0.17, 0.76], [0.58, 1.0]]),
  L("l", [[0.3, 0.1], [0.3, 1.0]]),
  L("m", [[0.1, 0.5], [0.1, 1.0]],
         [...boog(0.28, 0.18), [0.46, 1.0]],
         [...boog(0.64, 0.18), [0.82, 1.0]]),
  L("n", [[0.15, 0.5], [0.15, 1.0]], [...boog(0.4, 0.25), [0.65, 1.0]]),
  L("o", arc(-Math.PI / 2, -Math.PI / 2 - TAU, 36, 0.4, 0.75, 0.26, 0.26)),
  L("p", [[0.15, 0.5], [0.15, 1.35]],
         arc(-Math.PI / 2, Math.PI / 2, 18, 0.15, 0.75, 0.38, 0.25)),
  L("q", rondje(), [[0.65, 0.5], [0.65, 1.28], [0.79, 1.15]]),
  L("r", [[0.15, 0.5], [0.15, 1.0]],
         arc(Math.PI, 0.2 * Math.PI, 10, 0.39, 0.74, 0.24, -0.24)),
  L("s", [[0.60, 0.57], [0.5, 0.51], [0.36, 0.5], [0.25, 0.56], [0.22, 0.65],
          [0.3, 0.73], [0.45, 0.77], [0.56, 0.82], [0.6, 0.9], [0.55, 0.97],
          [0.42, 1.0], [0.29, 0.985], [0.2, 0.92]]),
  L("t", [[0.35, 0.2], [0.35, 0.82], ...arc(Math.PI, 0.35 * Math.PI, 8, 0.53, 0.82, 0.18, 0.17)],
         [[0.17, 0.5], [0.58, 0.5]]),
  L("u", [[0.15, 0.5], [0.15, 0.74], ...arc(Math.PI, 0, 16, 0.4, 0.74, 0.25, 0.24), [0.65, 0.5]]),
  L("v", [[0.12, 0.5], [0.4, 1.0], [0.68, 0.5]]),
  L("w", [[0.05, 0.5], [0.26, 1.0], [0.47, 0.58], [0.68, 1.0], [0.89, 0.5]]),
  L("x", [[0.15, 0.5], [0.62, 1.0]], [[0.62, 0.5], [0.15, 1.0]]),
  L("y", [[0.15, 0.5], [0.42, 1.0]], [[0.68, 0.5], [0.2, 1.38]]),
  L("z", [[0.15, 0.5], [0.62, 0.5], [0.15, 1.0], [0.62, 1.0]]),
];
