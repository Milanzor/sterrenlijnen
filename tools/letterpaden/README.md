# Letterpaden-generator

Genereert `js/letterpaden.js`: de penpaden van de Letter leer modus,
rechtstreeks afgeleid uit `assets/PlaywriteNL.ttf`, zodat het na te trekken
spoor precies het letterfont volgt.

Werkwijze per letter:
1. glyph groot renderen (freetype) en skeletoniseren (scikit-image);
2. skelet omzetten in een graaf van knopen (uiteinden/kruisingen) en edges;
3. een penpad door de graaf lopen zoals op school geschreven wordt:
   instap eerst, bij kruisingen zo recht mogelijk door, gefuseerde
   dubbelhalen (zoals de rechterkant van de a of de stok van de d) mogen
   twee keer, U-bochten bij pieken en pootjes, en de pen gaat alleen van
   het papier bij echt losse halen (t-streep, x, puntje van i/j);
4. paden normaliseren (x-hoogte 0.5, grondlijn 1.0) en wegschrijven.

Twijfelgevallen per letter staan als hints in `drive.py` (startpunt,
draairichting van rondjes, geforceerde richting bij enkele kruisingen).

Draaien:

    python -m venv venv && venv/bin/pip install fonttools numpy scikit-image pillow freetype-py
    venv/bin/python drive.py   # previews (sheet0..3.png) om de volgorde te checken
    venv/bin/python emit.py    # schrijft ../../js/letterpaden.js

Let op: `emit.py` schrijft met een absoluut pad; pas `OUT` aan naar de
lokale checkout.
