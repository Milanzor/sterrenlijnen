// Woordenbibliotheek voor de Woorden modus: korte klankzuivere leeswoorden
// (zoals in groep 3), samengesteld uit de halen van letters.js. Je trekt het
// woord letter voor letter, haal voor haal, in de schrijfvolgorde; elke
// letter krijgt zijn eigen kleur.

import { LETTERS, KADER } from "./letters.js";

const WOORDLIJST = ["ik", "aap", "kat", "vis", "zon", "bal", "mus", "sok",
                    "pen", "jas", "bus", "koe", "maan", "roos", "boom", "boot",
                    "poes", "huis", "ster", "vlag"];

const GAP = 0.06;  // ruimte tussen twee letters, in letter-eenheden —
                   // klein, want de uitstapjes van het schoolschrift
                   // overbruggen al bijna de hele afstand

const perLetter = new Map(LETTERS.map(l => {
  let minX = Infinity, maxX = -Infinity;
  for (const p of l.paths) for (const [x] of p) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
  }
  return [l.letter, { paths: l.paths, minX, maxX }];
}));

function woordSpec(woord) {
  const paths = [], groepen = [], badges = [];
  let cursor = 0;
  for (const [gi, ch] of [...woord].entries()) {
    const { paths: lp, minX, maxX } = perLetter.get(ch);
    const dx = cursor - minX;
    for (const [si, p] of lp.entries()) {
      paths.push(p.map(([x, y]) => [x + dx, y]));
      groepen.push(gi);
      badges.push(lp.length > 1 ? si + 1 : null);
    }
    cursor += (maxX - minX) + GAP;
  }
  return { name: woord, woord, toon: woord, strokes: true, duo: false,
           paths, groepen, badges, kader: KADER, banner: `${woord}!`,
           zegNieuw: woord, zegKlaar: woord };
}

export const WOORDEN = WOORDLIJST.map(woordSpec);
