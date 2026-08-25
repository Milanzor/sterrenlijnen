import math, numpy as np
from PIL import Image
import drive
from drive import process
from extract import smooth, resample, NORM

OUT = '/home/milan/projects-prive/sterrenlijnen/js/letterpaden.js'

def norm_pt(r, c, baseline, x0):
    return [round((c - x0) * NORM, 3), round(1.0 - (baseline - r) * NORM, 3)]

letters = {}
min_y, max_y = 1e9, -1e9
for ch in 'abcdefghijklmnopqrstuvwxyz':
    img, baseline, x0, out, dbg = process(ch)
    paths = []
    for o in out:
        if o[0] == 'stroke':
            pts = smooth([(float(r), float(c)) for r, c in o[1]], it=3)
            pts = resample(pts, 11.0)
            paths.append([norm_pt(r, c, baseline, x0) for r, c in pts])
        else:  # puntje (i/j): mini-rondje
            _, r, c = o
            cx, cy = norm_pt(r, c, baseline, x0)
            R, n = 0.045, 9
            paths.append([[round(cx + R*math.cos(-math.pi/2 - 2*math.pi*i/(n-1)), 3),
                           round(cy + R*math.sin(-math.pi/2 - 2*math.pi*i/(n-1)), 3)]
                          for i in range(n)])
    letters[ch] = paths
    for p in paths:
        for x, y in p:
            min_y = min(min_y, y); max_y = max(max_y, y)
    print(ch, [len(p) for p in paths])

print('minY', min_y, 'maxY', max_y)
kader_min = round(min_y - 0.04, 2)
kader_max = round(max_y + 0.04, 2)

with open(OUT, 'w') as f:
    f.write("// GEGENEREERD — niet met de hand bewerken.\n")
    f.write("// Pen-paden per letter, afgeleid uit assets/PlaywriteNL.ttf:\n")
    f.write("// skelet van elke glyph -> penvolgorde zoals op school (instap,\n")
    f.write("// lussen, dubbelhalen, puntje het laatst). Generator: de\n")
    f.write("// letterpaden-scripts in de sessie-scratchpad (freetype +\n")
    f.write("// skimage.skeletonize).\n")
    f.write("// Coördinaten: x-hoogte 0.5, grondlijn 1.0 (y omlaag);\n")
    f.write("// stokken tot ~%.2f, staarten tot ~%.2f.\n\n" % (min_y, max_y))
    f.write("export const KADER = { minY: %s, maxY: %s };\n" % (kader_min, kader_max))
    f.write("export const BOVENLIJN = %.2f;\n\n" % min_y)
    f.write("export const PADEN = {\n")
    for ch, paths in letters.items():
        f.write("  %s: [\n" % ch)
        for p in paths:
            f.write("    [" + ",".join("[%g,%g]" % (x, y) for x, y in p) + "],\n")
        f.write("  ],\n")
    f.write("};\n")
print('geschreven:', OUT)
