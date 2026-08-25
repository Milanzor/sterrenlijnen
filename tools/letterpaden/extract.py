"""Haal pen-paden (centerlines) uit PlaywriteNL.ttf via skeletonisatie.

Pijplijn per letter:
  render groot -> skeleton -> pixelgraaf (endpoints/junctions/edges)
  -> spurs weg -> pen-traversal (rechtdoor bij kruisingen, hint voor start)
  -> normaliseren (x-hoogte 0.5, grondlijn 1.0) -> preview + JS-data.
"""
import freetype, numpy as np, json, math
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize
from fontTools.ttLib import TTFont

FONT = '/home/milan/projects-prive/sterrenlijnen/assets/PlaywriteNL.ttf'
S = 560  # renderhoogte (em) in px

tt = TTFont(FONT)
UPEM = tt['head'].unitsPerEm
XH = tt['OS/2'].sxHeight / UPEM * S  # x-hoogte in px
NORM = 0.5 / XH                       # px -> normeenheden (x-hoogte = 0.5)

face = freetype.Face(FONT)
face.set_pixel_sizes(0, S)

def render(ch):
    face.load_char(ch, freetype.FT_LOAD_RENDER)
    g = face.glyph; b = g.bitmap
    img = np.array(b.buffer, dtype=np.uint8).reshape(b.rows, b.width)
    pad = 8
    out = np.zeros((b.rows + 2*pad, b.width + 2*pad), np.uint8)
    out[pad:-pad, pad:-pad] = img
    # (row,col) -> norm: y = 1 - (baseline_row - row)*NORM ; x = col*NORM
    baseline_row = g.bitmap_top + pad
    x0 = -(g.bitmap_left - pad)  # zodat norm-x ~ glyph-coördinaat
    return out, baseline_row, x0

def to_norm(pts, baseline_row, x0):
    return [[(c - x0) * NORM, 1.0 - (baseline_row - r) * NORM] for r, c in pts]

# ---------- skeletgraaf ----------
NB = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

def build_graph(sk):
    pix = set(zip(*np.nonzero(sk)))
    deg = {p: sum(((p[0]+dr, p[1]+dc) in pix) for dr, dc in NB) for p in pix}
    node_pix = {p for p in pix if deg[p] != 2}
    # cluster aangrenzende node-pixels
    clusters, seen = [], set()
    for p in node_pix:
        if p in seen: continue
        stack, comp = [p], []
        seen.add(p)
        while stack:
            q = stack.pop(); comp.append(q)
            for dr, dc in NB:
                n = (q[0]+dr, q[1]+dc)
                if n in node_pix and n not in seen:
                    seen.add(n); stack.append(n)
        clusters.append(comp)
    pix2node = {}
    nodes = []
    for i, comp in enumerate(clusters):
        for p in comp: pix2node[p] = i
        nodes.append((sum(p[0] for p in comp)/len(comp), sum(p[1] for p in comp)/len(comp)))
    # edges: wandel vanaf elke nodepixel door graad-2 kettingen
    edges = []  # (n1, n2, [pixelpad])
    used = set()  # (nodepixel, eerste graad-2 pixel)
    for p in node_pix:
        for dr, dc in NB:
            q = (p[0]+dr, p[1]+dc)
            if q not in pix: continue
            if q in node_pix:
                # directe node-node verbinding (verschillende clusters)
                if pix2node[q] != pix2node[p]:
                    key = tuple(sorted((p, q)))
                    if key in used: continue
                    used.add(key)
                    edges.append((pix2node[p], pix2node[q], [p, q]))
                continue
            if (p, q) in used: continue
            path = [p, q]
            used.add((p, q))
            prev, cur = p, q
            while cur not in node_pix:
                nxt = None
                for dr2, dc2 in NB:
                    n = (cur[0]+dr2, cur[1]+dc2)
                    if n in pix and n != prev and not (n in node_pix and pix2node.get(n) == pix2node.get(prev, -1)):
                        # kies buur die niet terug is
                        if n == prev: continue
                        nxt = n; break
                if nxt is None: break
                path.append(nxt)
                prev, cur = cur, nxt
                if cur in node_pix:
                    used.add((cur, prev))
                    break
            n2 = pix2node.get(cur, None)
            if n2 is None:  # losse punt? maak endpoint-node
                nodes.append(cur); n2 = len(nodes)-1; pix2node[cur] = n2
            edges.append((pix2node[p], n2, path))
    # geïsoleerde cycli (geen enkele node): pak willekeurige pixel als node
    edge_pix = set()
    for _,_,path in edges: edge_pix.update(path)
    left = pix - edge_pix - set(pix2node)
    while left:
        p = next(iter(left))
        nodes.append(p); pix2node[p] = len(nodes)-1
        # wandel de cykel rond
        path = [p]
        prev, cur = None, p
        while True:
            nxt = None
            for dr, dc in NB:
                n = (cur[0]+dr, cur[1]+dc)
                if n in pix and n != prev and (n in left or n == p):
                    nxt = n; break
            if nxt is None or nxt == p: 
                if nxt == p: path.append(p)
                break
            path.append(nxt); prev, cur = cur, nxt
        edges.append((pix2node[p], pix2node[p], path))
        left -= set(path)
    return nodes, edges

def prune(nodes, edges, min_len):
    """verwijder korte spurs (edge met een uiteinde van graad 1)"""
    while True:
        deg = {}
        for a, b, _ in edges:
            deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
        drop = None
        for i, (a, b, path) in enumerate(edges):
            if a != b and len(path) < min_len and (deg[a] == 1 or deg[b] == 1):
                drop = i; break
        if drop is None: return edges
        edges = edges[:drop] + edges[drop+1:]

def merge_degree2(nodes, edges):
    """na prunen: nodes met graad 2 wegwerken door edges te plakken"""
    changed = True
    while changed:
        changed = False
        deg = {}
        inc = {}
        for i, (a, b, _) in enumerate(edges):
            for n in (a, b):
                deg[n] = deg.get(n, 0) + 1
                inc.setdefault(n, []).append(i)
        for n, d in deg.items():
            if d == 2 and len(set(inc[n])) == 2:
                i, j = inc[n]
                a1, b1, p1 = edges[i]; a2, b2, p2 = edges[j]
                if a1 == b1 or a2 == b2: continue
                if b1 != n: a1, b1, p1 = b1, a1, p1[::-1]
                if a2 != n: a2, b2, p2 = b2, a2, p2[::-1]
                new = (a1, b2, p1 + p2[1:])
                edges = [e for k, e in enumerate(edges) if k not in (i, j)] + [new]
                changed = True
                break
    return edges

def edge_dir(path, at_start, k=14):
    """richting van een edge, gezien vanaf een uiteinde, als eenheidsvector"""
    pts = path[:k] if at_start else path[::-1][:k]
    dr = pts[-1][0] - pts[0][0]; dc = pts[-1][1] - pts[0][1]
    n = math.hypot(dr, dc) or 1
    return (dr/n, dc/n)

def traverse(nodes, edges, start_node, start_dir):
    """pen-pad: volg edges, bij kruisingen zo recht mogelijk door.
    Elke edge max 2x (retrace toegestaan met straf)."""
    use = [0]*len(edges)
    inc = {}
    for i, (a, b, _) in enumerate(edges):
        inc.setdefault(a, []).append((i, True))
        inc.setdefault(b, []).append((i, False))
        if a == b: pass
    out = []
    cur, d = start_node, start_dir
    total = len(edges)
    while sum(1 for u in use if u > 0) < total:
        best, best_score = None, -1e9
        for i, fwd in inc.get(cur, []):
            if use[i] >= 2: continue
            a, b, path = edges[i]
            p = path if fwd else path[::-1]
            ed = edge_dir(p, True)
            dot = d[0]*ed[0] + d[1]*ed[1] if d else 0
            score = dot - use[i]*3.0
            if score > best_score:
                best_score, best = score, (i, p)
        if best is None:
            # vast: spring naar dichtstbijzijnde node met ongebruikte edge
            cand = [(i, e) for i, e in enumerate(edges) if use[i] == 0]
            if not cand: break
            cr, cc = nodes[cur] if cur < len(nodes) else (0, 0)
            def ndist(n): return (nodes[n][0]-cr)**2 + (nodes[n][1]-cc)**2
            i, (a, b, path) = min(cand, key=lambda t: min(ndist(t[1][0]), ndist(t[1][1])))
            p = path if ndist(a) <= ndist(b) else path[::-1]
            out.append(None)  # pen omhoog
            best = (i, p)
        i, p = best
        use[i] += 1
        out.append(p)
        cur = edges[i][1] if p[0] == edges[i][2][0] else edges[i][0]
        # cur = node aan het einde van p
        endpix = p[-1]
        # vind node het dichtst bij endpix
        cur = min(range(len(nodes)), key=lambda n: (nodes[n][0]-endpix[0])**2 + (nodes[n][1]-endpix[1])**2)
        d = edge_dir(p, False)
        d = (-d[0], -d[1])  # richting waarin we bewegen aan het eind
    # plak aaneengesloten stukken
    strokes, cur_pts = [], []
    for seg in out:
        if seg is None:
            if cur_pts: strokes.append(cur_pts); cur_pts = []
            continue
        if cur_pts and cur_pts[-1] != seg[0]:
            strokes.append(cur_pts); cur_pts = []
        cur_pts = cur_pts + (seg if not cur_pts else seg[1:])
    if cur_pts: strokes.append(cur_pts)
    return strokes

def smooth(pts, it=2):
    for _ in range(it):
        if len(pts) < 5: return pts
        out = [pts[0]]
        for i in range(1, len(pts)-1):
            out.append(((pts[i-1][0]+2*pts[i][0]+pts[i+1][0])/4,
                        (pts[i-1][1]+2*pts[i][1]+pts[i+1][1])/4))
        out.append(pts[-1])
        pts = out
    return pts

def resample(pts, step):
    if len(pts) < 2: return pts
    out = [pts[0]]; acc = 0.0
    for i in range(1, len(pts)):
        x0, y0 = pts[i-1]; x1, y1 = pts[i]
        d = math.hypot(x1-x0, y1-y0)
        while acc + d >= step:
            t = (step - acc) / d
            nx, ny = x0 + (x1-x0)*t, y0 + (y1-y0)*t
            out.append((nx, ny))
            x0, y0 = nx, ny
            d = math.hypot(x1-x0, y1-y0); acc = 0.0
        acc += d
    if out[-1] != pts[-1]: out.append(pts[-1])
    return out
