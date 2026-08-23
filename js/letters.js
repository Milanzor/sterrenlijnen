// Letterbibliotheek voor de Letter leer modus: alle 26 kleine letters in
// lopend schoolschrift, met penpaden die rechtstreeks uit het letterfont
// (assets/PlaywriteNL.ttf) zijn afgeleid — zie js/letterpaden.js. Het na te
// trekken spoor is dus precies de letter die het kind ernaast ziet staan.
//
// Elke letter is één doorlopende haal in de echte schrijfvolgorde (instap,
// lussen, dubbelhalen zoals bij de n en de d). Alleen i, j, t en x hebben
// een tweede haal (puntje of streepje) — die komt ná de hoofdhaal, met een
// cijfertje erbij, zoals in een schrijfschrift.
//
// Coördinaten: y omlaag, vaste schrijflijnen: x-hoogte 0.5, grondlijn 1.0,
// stokken tot BOVENLIJN (~-0.26), staarten tot ~1.76.

import { PADEN, KADER, BOVENLIJN } from "./letterpaden.js";
export { KADER, BOVENLIJN };

function L(letter) {
  const paths = PADEN[letter];
  return { name: `de letter ${letter}`, letter, toon: letter, strokes: true,
           duo: false, paths, kader: KADER, banner: `de ${letter}!`,
           zegNieuw: `de letter ${letter}`, zegKlaar: letter,
           badges: paths.length > 1 ? paths.map((_, i) => i + 1) : null };
}

export const LETTERS = [..."abcdefghijklmnopqrstuvwxyz"].map(L);
