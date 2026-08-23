"""Skeletgraaf v2: elke ketting van graad-2 pixels wordt precies één edge."""
import numpy as np, math

NB = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

def build_graph(sk):
    pix = set(zip(*np.nonzero(sk)))
    nbrs = {p: [(p[0]+dr, p[1]+dc) for dr, dc in NB if (p[0]+dr, p[1]+dc) in pix]
            for p in pix}
    node_pix = {p for p in pix if len(nbrs[p]) != 2}
    # cluster aangrenzende node-pixels tot één knoop
    pix2node, nodes, seen = {}, [], set()
    for p in sorted(node_pix):
        if p in seen: continue
        stack, comp = [p], []
        seen.add(p)
        while stack:
            q = stack.pop(); comp.append(q)
            for n in nbrs[q]:
                if n in node_pix and n not in seen:
                    seen.add(n); stack.append(n)
        i = len(nodes)
        nodes.append((sum(q[0] for q in comp)/len(comp),
                      sum(q[1] for q in comp)/len(comp)))
        for q in comp: pix2node[q] = i

    edges, consumed, direct = [], set(), set()
    for p in sorted(node_pix):
        for q in nbrs[p]:
            if q in node_pix:
                a, b = pix2node[p], pix2node[q]
                if a != b:
                    key = (min(a, b), max(a, b), tuple(sorted((p, q))))
                    if key not in direct:
                        direct.add(key)
                        edges.append((a, b, [p, q]))
                continue
            if q in consumed: continue
            path, prev, cur = [p, q], p, q
            consumed.add(q)
            while cur not in node_pix:
                nxt = None
                for n in nbrs[cur]:
                    if n == prev: continue
                    if n in node_pix: nxt = n; break
                    if n not in consumed: nxt = n
                if nxt is None: break
                if nxt not in node_pix: consumed.add(nxt)
                path.append(nxt)
                prev, cur = cur, nxt
            if cur in node_pix:
                edges.append((pix2node[p], pix2node[cur], path))

    # losse cycli zonder enige knoop
    remaining = pix - consumed - node_pix
    while remaining:
        p = remaining.pop()
        nodes.append(p); pix2node[p] = len(nodes)-1
        path, prev, cur = [p], None, p
        while True:
            nxt = None
            for n in nbrs[cur]:
                if n == prev: continue
                if n in remaining: nxt = n; break
                if n == p and len(path) > 2: nxt = p; break
            if nxt is None: break
            path.append(nxt)
            if nxt == p: break
            remaining.discard(nxt)
            prev, cur = cur, nxt
        edges.append((pix2node[p], pix2node[p], path))
    return nodes, edges

def _deg(edges):
    deg = {}
    for a, b, _ in edges:
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    return deg

def simplify(nodes, edges, min_spur):
    """herhaald: korte spurs en mini-zelfluzen weg, graad-2 knopen samenvoegen"""
    changed = True
    while changed:
        changed = False
        deg = _deg(edges)
        # korte spur (uiteinde met graad 1) of mini-zelflus
        for i, (a, b, path) in enumerate(edges):
            if len(path) < min_spur and (a == b or deg[a] == 1 or deg[b] == 1) \
               and len(edges) > 1:
                edges = edges[:i] + edges[i+1:]
                changed = True
                break
        if changed: continue
        # graad-2 knoop: plak de twee edges aan elkaar
        deg = _deg(edges)
        inc = {}
        for i, (a, b, _) in enumerate(edges):
            inc.setdefault(a, []).append(i)
            inc.setdefault(b, []).append(i)
        for n, d in deg.items():
            if d != 2: continue
            ii = inc[n]
            if len(set(ii)) != 2: continue  # zelflus
            i, j = sorted(set(ii))
            a1, b1, p1 = edges[i]; a2, b2, p2 = edges[j]
            if b1 != n: a1, b1, p1 = b1, a1, p1[::-1]
            if a2 != n: a2, b2, p2 = b2, a2, p2[::-1]
            new = (a1, b2, p1 + p2[1:])
            edges = [e for k, e in enumerate(edges) if k not in (i, j)] + [new]
            changed = True
            break
    return edges

def _dir(path, k=16):
    k = min(k, len(path))
    dr = path[k-1][0] - path[0][0]; dc = path[k-1][1] - path[0][1]
    n = math.hypot(dr, dc) or 1
    return (dr/n, dc/n)

def traverse(nodes, edges, start, start_dir, dir2=None, lift=False, jump=None,
             dir_steps=None, max_use=2):
    """Penpad door de skeletgraaf, zoals een echte pen schrijft:
    - ongebruikte edges eerst, zo recht mogelijk door (bocht-cutoff);
    - gefuseerde dubbelhalen (bijv. de rechterkant van de a, de stok van de d)
      mogen 2x, mits dat nog ergens heen leidt (bereikbaarheids-check);
    - U-bocht (retrace) mag, behalve bij lift-letters (t, x): die tillen de
      pen op en springen naar de jump-hint (aparte haal, zoals de t-streep).
    """
    use = [0]*len(edges)
    inc = {}
    for i, (a, b, path) in enumerate(edges):
        inc.setdefault(a, []).append((i, True))
        inc.setdefault(b, []).append((i, False))  # zelflus: beide richtingen

    def unused_reachable(frm, u):
        seen, stack = {frm}, [frm]
        while stack:
            n = stack.pop()
            for i, fwd in inc.get(n, []):
                if u[i] == 0: return True
                if u[i] >= max_use: continue
                a, b, _ = edges[i]
                o = b if n == a else a
                if o not in seen:
                    seen.add(o); stack.append(o)
        return False

    def leads_on(i, endnode):
        u = use[:]; u[i] += 1
        return unused_reachable(endnode, u)

    strokes, cur_pts, cur, d, step = [], [], start, start_dir, 0
    last_edge = None
    while any(u == 0 for u in use):
        want = d
        if dir_steps and step in dir_steps: want = dir_steps[step]
        elif dir2 and step == 1: want = dir2
        cands = []
        for i, fwd in inc.get(cur, []):
            if use[i] >= max_use: continue
            a, b, path = edges[i]
            p = path if fwd else path[::-1]
            end = b if fwd else a
            ed = _dir(p)
            dot = want[0]*ed[0] + want[1]*ed[1]
            cands.append((i, p, end, dot))
        best = None
        fresh = [c for c in cands if use[c[0]] == 0 and c[3] > -0.6 and leads_on(c[0], c[2])]
        if not fresh:  # zonder bereikbaarheids-eis (laatste edge mag doodlopen)
            fresh = [c for c in cands if use[c[0]] == 0 and c[3] > -0.6]
        # hergebruik van een gefuseerde dubbelhaal alleen als hij duidelijk
        # rechter doorloopt dan de beste verse edge (of als er niets vers is);
        # een gesloten lus schrijft een pen nooit twee keer
        reuse = [c for c in cands if use[c[0]] >= 1 and c[3] > 0.4
                 and edges[c[0]][0] != edges[c[0]][1]
                 and leads_on(c[0], c[2])]
        fbest = max(fresh, key=lambda c: c[3]) if fresh else None
        rbest = max(reuse, key=lambda c: c[3]) if reuse else None
        if rbest and (not fbest or rbest[3] - fbest[3] > 0.3):
            best = rbest
        elif fbest:
            best = fbest
        elif not lift and last_edge is not None:
            # U-bocht terug over de zojuist getrokken edge (piek/pootje) —
            # maar niet als er alleen nog kruimel-edges te halen zijn
            if sum(len(e[2]) for j, e in enumerate(edges) if use[j] == 0) >= 120:
                back = [c for c in cands if c[0] == last_edge and leads_on(c[0], c[2])]
                if back: best = back[0]
        if best is None:
            # pen van het papier: naar de start van de volgende losse haal
            if cur_pts: strokes.append(cur_pts); cur_pts = []
            unused = [(i, e) for i, e in enumerate(edges) if use[i] == 0]
            if sum(len(e[2]) for _, e in unused) < 120: break
            if not unused: break
            if jump:
                tr, tc = jump
                def key(t):
                    i, (a, b, _) = t
                    return min((nodes[n][0]-tr)**2 + (nodes[n][1]-tc)**2 for n in (a, b))
            else:
                def key(t):
                    i, (a, b, _) = t
                    return min(nodes[a][0], nodes[b][0])
            i, (a, b, path) = min(unused, key=key)
            if jump:
                fwd = ((nodes[a][0]-tr)**2 + (nodes[a][1]-tc)**2 <=
                       (nodes[b][0]-tr)**2 + (nodes[b][1]-tc)**2)
            else:
                fwd = nodes[a][0] <= nodes[b][0]
            best = (i, path if fwd else path[::-1], b if fwd else a, 0)
        i, p, endnode, _ = best
        import os
        if os.environ.get('TRACE'):
            print(f'   stap {step}: node {cur} -> edge {i} -> node {endnode} '
                  f'(use wordt {use[i]+1}) dot {best[3]:.2f} | opties: '
                  + '; '.join(f'e{c[0]}(u{use[c[0]]},dot {c[3]:.2f})' for c in cands))
        use[i] += 1
        last_edge = i
        if cur_pts:
            gap = math.hypot(cur_pts[-1][0]-p[0][0], cur_pts[-1][1]-p[0][1])
            if gap > 40:
                strokes.append(cur_pts); cur_pts = []
        cur_pts = cur_pts + (p if not cur_pts else p[1:])
        cur = endnode
        dd = _dir(p[::-1])
        d = (-dd[0], -dd[1])
        step += 1
    if cur_pts: strokes.append(cur_pts)
    return strokes
