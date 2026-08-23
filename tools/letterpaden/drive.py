import numpy as np, math, colorsys
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize
from skimage.measure import label
from extract import render, smooth, resample, NORM, S, XH
from graph2 import build_graph, simplify, traverse, _deg, _dir

# starthints: (fx, fy) in bbox-fracties van de hoofdcomponent (0,0=linksboven),
# richting (dr, dc) in pixelcoördinaten (rij omlaag).
ROND   = {'start': (0.85, 0.10), 'dir': (-0.3, -1)}    # 2 uur, linksom
INSTAP = {'start': (0.0, 1.0),  'dir': (-1, 0.4)}      # linksonder, omhoog
HINTS = {
  'a': dict(ROND, dir2=(-0.2, -1), rond=True), 'c': dict(ROND),
  'd': dict(ROND, rond=True), 'g': dict(ROND, dir2=(-0.2, -1), rond=True),
  'o': dict(ROND), 'q': dict(ROND, dir2=(-0.2, -1), rond=True),
  'e': {'start': (0.0, 0.6), 'dir': (-0.4, 1)},
  'b': dict(INSTAP),
  'f': dict(INSTAP, max_use=3, dir_steps={2: (-1, 0), 9: (-1, 0)}),
  'h': dict(INSTAP, max_use=3, dir_steps={2: (-1, 0.2)}),
  'k': dict(INSTAP, max_use=3, dir_steps={5: (1, -0.5), 15: (0.7, 0.7)}),
  'l': dict(INSTAP), 'i': dict(INSTAP), 'j': dict(INSTAP),
  'm': {'start': (0.0, 0.4), 'dir': (-0.6, 1)},
  'n': {'start': (0.0, 0.4), 'dir': (-0.6, 1)},
  'p': dict(INSTAP), 'r': dict(INSTAP), 's': dict(INSTAP),
  't': {'start': (0.4, 0.0), 'dir': (1, 0), 'lift': True, 'jump': (0.0, 0.45),
        'dir_steps': {1: (1, -0.2), 2: (1, 0.1)}},
  'u': {'start': (0.0, 0.1), 'dir': (1, 0.3)},
  'v': {'start': (0.0, 0.1), 'dir': (1, 0.3)},
  'w': {'start': (0.0, 0.1), 'dir': (1, 0.3)},
  'x': {'start': (0.0, 0.0), 'dir': (1, 0.5), 'lift': True, 'jump': (1.0, 0.0)},
  'y': {'start': (0.0, 0.1), 'dir': (1, 0.3)},
  'z': {'start': (0.0, 0.0), 'dir': (0, 1)},
}

def component_strokes(m, hint):
    nodes, edges = build_graph(m)
    edges = simplify(nodes, edges, 24)
    if not edges: return [], nodes, edges
    rows, cols = np.nonzero(m)
    if len(edges) == 1 and edges[0][0] == edges[0][1] and len(edges[0][2]) > 60:
        # pure cykel (zoals de o): draai zodat hij bij de hint begint,
        # richting volgens de hint
        path = edges[0][2]
        if path[0] == path[-1]: path = path[:-1]
        r0, r1 = rows.min(), rows.max(); c0, c1 = cols.min(), cols.max()
        hr = r0 + hint['start'][1] * (r1 - r0)
        hc = c0 + hint['start'][0] * (c1 - c0)
        k = min(range(len(path)), key=lambda i: (path[i][0]-hr)**2 + (path[i][1]-hc)**2)
        rot = path[k:] + path[:k]
        d = hint['dir']; ln = math.hypot(*d) or 1
        fwd = _dir(rot)
        dot = (d[0]*fwd[0] + d[1]*fwd[1]) / ln
        if dot < 0: rot = [rot[0]] + rot[1:][::-1]
        return [rot + [rot[0]]], nodes, edges
    r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()
    diag = math.hypot(r1-r0, c1-c0)
    hr = r0 + hint['start'][1] * (r1 - r0)
    hc = c0 + hint['start'][0] * (c1 - c0)
    deg = _deg(edges)
    if hint.get('rond'):
        # ronde letters (a/d/g/q): start op '1 uur' van het rondje = de
        # meest rechtse knoop in de bovenste helft van de x-hoogte-band
        from extract import XH as _XH
        band = [n for n in deg if BASELINE[0] - 1.15*_XH <= nodes[n][0] <= BASELINE[0] - 0.6*_XH]
        start = max(band or list(deg), key=lambda n: nodes[n][1])
    else:
        def score(n):
            d = math.hypot(nodes[n][0]-hr, nodes[n][1]-hc)
            return d - (0.25 * diag if deg.get(n) == 1 else 0)
        start = min(deg, key=score)
    d = hint['dir']; ln = math.hypot(*d) or 1
    d2 = hint.get('dir2')
    if d2:
        l2 = math.hypot(*d2) or 1
        d2 = (d2[0]/l2, d2[1]/l2)
    jump = hint.get('jump')
    if jump:
        r0_, r1_ = rows.min(), rows.max(); c0_, c1_ = cols.min(), cols.max()
        jump = (r0_ + jump[1]*(r1_-r0_), c0_ + jump[0]*(c1_-c0_))
    strokes = traverse(nodes, edges, start, (d[0]/ln, d[1]/ln), dir2=d2,
                       lift=hint.get('lift', False), jump=jump,
                       dir_steps=hint.get('dir_steps'),
                       max_use=hint.get('max_use', 2))
    strokes = [s for s in strokes if sum(math.hypot(s[i][0]-s[i-1][0],
               s[i][1]-s[i-1][1]) for i in range(1, len(s))) > 110]
    return strokes, nodes, edges

BASELINE = [0]

def process(ch):
    img, baseline, x0 = render(ch)
    BASELINE[0] = baseline
    sk = skeletonize(img > 100)
    lab = label(sk, connectivity=2)
    comps = sorted((( (lab==i).sum(), i) for i in range(1, lab.max()+1)), reverse=True)
    out, dbg = [], []
    for _, i in comps:
        m = lab == i
        rows, cols = np.nonzero(m)
        if max(rows.max()-rows.min(), cols.max()-cols.min()) < 0.18 * XH:
            out.append(('dot', rows.mean(), cols.mean()))
            continue
        strokes, nodes, edges = component_strokes(m, HINTS[ch])
        out.extend(('stroke', s) for s in strokes)
        deg = _deg(edges)
        dbg.append([nodes[n] for n in deg if deg[n] == 1])
    return img, baseline, x0, out, dbg

def preview(ch, img, out, dbg):
    im = Image.fromarray(255 - (img//3)).convert('RGB')
    dr = ImageDraw.Draw(im)
    strokes = [o for o in out if o[0] == 'stroke']
    total = sum(len(s[1]) for s in strokes) or 1
    seen = 0
    for si, (_, s) in enumerate(strokes):
        for i in range(1, len(s)):
            t = (seen + i) / total
            rgb = tuple(int(c*255) for c in colorsys.hsv_to_rgb(0.66*(1-t), 0.9, 0.85))
            dr.line([(s[i-1][1], s[i-1][0]), (s[i][1], s[i][0])], fill=rgb, width=4)
        seen += len(s)
        r, c = s[0]
        dr.ellipse([c-10, r-10, c+10, r+10], outline=(0,150,0), width=5)
    for ends in dbg:
        for r, c in ends:
            dr.rectangle([c-5, r-5, c+5, r+5], outline=(255,0,255), width=3)
    for o in out:
        if o[0] == 'dot':
            _, r, c = o
            dr.ellipse([c-8, r-8, c+8, r+8], fill=(220,130,0))
    return im

if __name__ == '__main__':
    CH, CW, BASE = 1150, 560, 760
    cells = []
    for ch in 'abcdefghijklmnopqrstuvwxyz':
        img, baseline, x0, out, dbg = process(ch)
        im = preview(ch, img, out, dbg)
        cell = Image.new('RGB', (CW, CH), (255,255,255))
        cell.paste(im, (40, BASE - baseline))
        d = ImageDraw.Draw(cell)
        d.line([(0, BASE), (CW, BASE)], fill=(215,215,215))
        d.line([(0, BASE-int(XH)), (CW, BASE-int(XH))], fill=(232,232,232))
        d.text((10, 10), ch, fill=(0,0,0))
        cells.append(cell)
        print(ch, 'strokes:', [len(o[1]) for o in out if o[0]=='stroke'],
              'dots:', sum(1 for o in out if o[0]=='dot'))
    for s in range(4):
        blad = Image.new('RGB', (CW*7, CH), (255,255,255))
        for i, cell in enumerate(cells[s*7:(s+1)*7]):
            blad.paste(cell, (i*CW, 0))
        blad = blad.resize((CW*7//2, CH//2))
        blad.save(f'sheet{s}.png')
    print('sheets ok')
