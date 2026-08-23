"""Visuele stijl: digigamez "observatorium + cockpit" palet, Baloo 2, sprites.

Alle sprites worden één keer vooraf gerenderd (numpy → pygame.Surface) zodat de
renderlus alleen goedkope blits doet.
"""
import math
import os

import numpy as np
import pygame

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

VOID_DEEP = (5, 7, 15)
VOID = (13, 12, 34)
AMBER = (255, 194, 74)

# Speelkleuren uit digigamez
TEAL = (95, 227, 196)
CORAL = (255, 107, 107)
LILA = (197, 160, 255)
SKY = (120, 200, 255)
LIME = (190, 235, 120)
ROSE = (255, 160, 210)

PLAY_COLORS = [TEAL, CORAL, LILA, SKY, LIME, ROSE]

_fonts: dict[tuple[int, bool], pygame.font.Font] = {}


def font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _fonts:
        f = pygame.font.Font(os.path.join(ASSETS, "Baloo2.ttf"), size)
        f.set_bold(bold)
        _fonts[key] = f
    return _fonts[key]


def load_frames(subdir: str, height: int) -> list[pygame.Surface]:
    """PNG-framereeks uit assets/sprites/<subdir> laden, geschaald op hoogte.

    Enige niet-procedurele sprites in het spel (CC0, zie sprites/LICENSES.md).
    """
    folder = os.path.join(ASSETS, "sprites", subdir)
    frames = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".png"):
            continue
        img = pygame.image.load(os.path.join(folder, name)).convert_alpha()
        w = round(img.get_width() * height / img.get_height())
        frames.append(pygame.transform.smoothscale(img, (w, height)))
    return frames


def _surface_from_rgba(rgba: np.ndarray) -> pygame.Surface:
    h, w = rgba.shape[:2]
    return pygame.image.frombuffer(rgba.tobytes(), (w, h), "RGBA").convert_alpha()


def make_glow(radius: int, color, peak: int = 255, falloff: float = 2.2) -> pygame.Surface:
    """Zachte radiale gloed voor vingertoppen, sterren en deeltjes.

    Let op: bij BLEND_ADD negeert SDL de alfakanalen, dus het verloop zit in
    de RGB-waarden zelf (zwart telt niets op) én in alfa voor normale blits.
    """
    d = radius * 2
    y, x = np.ogrid[:d, :d]
    r = np.sqrt((x - radius + 0.5) ** 2 + (y - radius + 0.5) ** 2) / radius
    k = np.clip(1.0 - r, 0.0, 1.0) ** falloff * (peak / 255.0)
    rgba = np.zeros((d, d, 4), dtype=np.uint8)
    for i, c in enumerate(color):
        rgba[..., i] = (k * c).astype(np.uint8)
    rgba[..., 3] = (k * 255).astype(np.uint8)
    return _surface_from_rgba(rgba)


def make_glow_levels(radius: int, color, peak: int = 255, falloff: float = 2.2, n: int = 5) -> list:
    """Helderheidstrapjes van dezelfde gloed, voor uitdovende additieve deeltjes."""
    return [make_glow(radius, color, max(8, int(peak * (i + 1) / n)), falloff) for i in range(n)]


def make_bubble(radius: int, color) -> pygame.Surface:
    """Zeepbel: doorschijnend lijf, heldere rand, twee glimlichten, lichte kleurzweem."""
    d = radius * 2
    y, x = np.ogrid[:d, :d]
    nx = (x - radius + 0.5) / radius
    ny = (y - radius + 0.5) / radius
    r = np.sqrt(nx ** 2 + ny ** 2)
    inside = r <= 1.0

    body = np.clip(0.20 + 0.26 * r ** 3, 0, 1)              # lijf: bijna doorzichtig hart
    rim = np.exp(-((r - 0.93) / 0.06) ** 2) * 0.85          # rand als instrumentglas
    alpha = np.where(inside, np.clip(body + rim, 0, 1) * 255, 0)

    c = np.array(color, dtype=np.float64)
    c2 = np.array([255, 255, 255], dtype=np.float64)
    # iriserend: witachtig hart, sterk gekleurde rand (zoals een echte zeepbel)
    mix = np.clip(r[..., None] * 1.05, 0, 1) ** 1.5
    shade = np.clip((nx + ny)[..., None] * 0.18 + 0.5, 0, 1)
    col = (c2 * (1 - mix) + c * mix) * (0.86 + 0.28 * shade)

    rgba = np.zeros((d, d, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(col, 0, 255).astype(np.uint8)
    rgba[..., 3] = alpha.astype(np.uint8)
    surf = _surface_from_rgba(rgba)

    # glimlichten
    hl = pygame.Surface((d, d), pygame.SRCALPHA)
    big = pygame.Rect(0, 0, int(radius * 0.62), int(radius * 0.38))
    big.center = (int(radius * 0.62), int(radius * 0.52))
    pygame.draw.ellipse(hl, (255, 255, 255, 130), big)
    small = pygame.Rect(0, 0, int(radius * 0.18), int(radius * 0.13))
    small.center = (int(radius * 1.32), int(radius * 1.42))
    pygame.draw.ellipse(hl, (255, 255, 255, 90), small)
    surf.blit(hl, (0, 0))
    return surf


def _supersample(draw_fn, size: int, ss: int = 3) -> pygame.Surface:
    """pygame.draw kent geen anti-aliasing: teken op 3× en schaal glad terug."""
    return pygame.transform.smoothscale(draw_fn(size * ss), (size, size))


def make_star(radius: int, color=AMBER, glow: bool = True) -> pygame.Surface:
    pad = radius if glow else 4
    size = radius * 2 + pad * 2

    def poly(sz: int) -> pygame.Surface:
        f = sz / size
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        c = sz // 2
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = (radius if i % 2 == 0 else radius * 0.45) * f
            pts.append((c + math.cos(ang) * rr, c + math.sin(ang) * rr))
        pygame.draw.polygon(surf, color, pts)
        lighter = tuple(min(255, int(v + 70)) for v in color)
        pygame.draw.polygon(surf, lighter, pts, width=max(2, int(radius * f) // 10))
        return surf

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    if glow:
        g = make_glow(radius + pad, color, peak=110)
        surf.blit(g, (size // 2 - radius - pad, size // 2 - radius - pad))
    surf.blit(_supersample(poly, size), (0, 0))
    return surf


def make_alien(size: int) -> pygame.Surface:
    return _supersample(_draw_alien, size)


def _draw_alien(size: int) -> pygame.Surface:
    """Klein groen ruimtewezentje: passagier in een bel, zwaait bij ontsnappen."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    body = (150, 235, 120)
    dark = (95, 175, 80)
    # antennes
    for dx in (-16, 16):
        pygame.draw.line(s, dark, (50 * u + dx * u, 34 * u), (50 * u + dx * u * 1.6, 12 * u), max(2, int(3 * u)))
        pygame.draw.circle(s, AMBER, (int(50 * u + dx * u * 1.6), int(12 * u)), int(5 * u))
    # lijf + hoofd in één druppel
    pygame.draw.ellipse(s, body, pygame.Rect(24 * u, 26 * u, 52 * u, 58 * u))
    # zwaai-arm (omhoog)
    pygame.draw.line(s, body, (72 * u, 52 * u), (90 * u, 30 * u), max(3, int(9 * u)))
    pygame.draw.circle(s, body, (int(90 * u), int(30 * u)), int(6 * u))
    # andere arm
    pygame.draw.line(s, body, (28 * u, 56 * u), (14 * u, 68 * u), max(3, int(8 * u)))
    # ogen
    for dx in (-11, 11):
        pygame.draw.ellipse(s, (255, 255, 255), pygame.Rect((50 + dx - 7) * u, 38 * u, 14 * u, 18 * u))
        pygame.draw.circle(s, (20, 20, 40), (int((50 + dx) * u), int(48 * u)), int(4.5 * u))
    # mond
    pygame.draw.arc(s, dark, pygame.Rect(41 * u, 56 * u, 18 * u, 12 * u), math.pi, 2 * math.pi * 0.98, max(2, int(3 * u)))
    # voetjes
    for dx in (-12, 12):
        pygame.draw.ellipse(s, dark, pygame.Rect((50 + dx - 8) * u, 80 * u, 16 * u, 9 * u))
    return s


def make_chick(size: int) -> pygame.Surface:
    return _supersample(_draw_chick, size)


def _draw_chick(size: int) -> pygame.Surface:
    """Kuikentje: geel bolletje met kuifje, snaveltje en vleugeltjes."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    body = (255, 224, 92)
    wing = (238, 188, 58)
    orange = (255, 150, 60)
    ink = (35, 32, 58)
    # kuifje
    for dx in (-7, 0, 7):
        pygame.draw.line(s, wing, (50 * u + dx * u, 32 * u),
                         ((50 + dx * 1.7) * u, 20 * u), max(2, int(3 * u)))
    # lijfje
    pygame.draw.ellipse(s, body, pygame.Rect(24 * u, 28 * u, 52 * u, 60 * u))
    # vleugeltjes
    pygame.draw.ellipse(s, wing, pygame.Rect(15 * u, 50 * u, 16 * u, 26 * u))
    pygame.draw.ellipse(s, wing, pygame.Rect(69 * u, 50 * u, 16 * u, 26 * u))
    # oogjes
    for dx in (-10, 10):
        pygame.draw.ellipse(s, (255, 255, 255), pygame.Rect((50 + dx - 6) * u, 42 * u, 12 * u, 15 * u))
        pygame.draw.circle(s, ink, (int((50 + dx) * u), int(51 * u)), int(3.6 * u))
    # blosjes
    for dx in (-17, 17):
        pygame.draw.circle(s, (255, 150, 150), (int((50 + dx) * u), int(61 * u)), int(4 * u))
    # snaveltje
    pygame.draw.polygon(s, orange, [(43 * u, 58 * u), (57 * u, 58 * u), (50 * u, 68 * u)])
    # voetjes
    for dx in (-10, 10):
        pygame.draw.ellipse(s, orange, pygame.Rect((50 + dx - 6) * u, 86 * u, 12 * u, 7 * u))
    return s


def make_frog(size: int) -> pygame.Surface:
    return _supersample(_draw_frog, size)


def _draw_frog(size: int) -> pygame.Surface:
    """Kikkertje: groen, bolle ogen bovenop, brede lach."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    body = (118, 214, 104)
    dark = (78, 162, 70)
    belly = (198, 240, 182)
    ink = (35, 32, 58)
    # achterpootjes
    pygame.draw.ellipse(s, dark, pygame.Rect(8 * u, 68 * u, 28 * u, 20 * u))
    pygame.draw.ellipse(s, dark, pygame.Rect(64 * u, 68 * u, 28 * u, 20 * u))
    # lijf
    pygame.draw.ellipse(s, body, pygame.Rect(20 * u, 34 * u, 60 * u, 54 * u))
    # buikje
    pygame.draw.ellipse(s, belly, pygame.Rect(33 * u, 58 * u, 34 * u, 26 * u))
    # oogbollen
    for dx in (-16, 16):
        pygame.draw.circle(s, body, (int((50 + dx) * u), int(32 * u)), int(12.5 * u))
        pygame.draw.circle(s, (255, 255, 255), (int((50 + dx) * u), int(31 * u)), int(8.5 * u))
        pygame.draw.circle(s, ink, (int((50 + dx) * u), int(33 * u)), int(4 * u))
    # neusgaatjes
    for dx in (-5, 5):
        pygame.draw.circle(s, dark, (int((50 + dx) * u), int(44 * u)), max(1, int(1.8 * u)))
    # brede lach
    pygame.draw.arc(s, dark, pygame.Rect(34 * u, 40 * u, 32 * u, 16 * u),
                    math.pi * 1.05, math.pi * 1.95, max(2, int(3 * u)))
    # blosjes
    for dx in (-22, 22):
        pygame.draw.circle(s, (255, 150, 150), (int((50 + dx) * u), int(54 * u)), int(3.6 * u))
    return s


def make_bunny(size: int) -> pygame.Surface:
    return _supersample(_draw_bunny, size)


def _draw_bunny(size: int) -> pygame.Surface:
    """Roze konijntje: lange oren, snuitje met snorharen."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    fur = (255, 208, 226)
    inner = (255, 246, 250)
    rose = (235, 120, 160)
    ink = (35, 32, 58)
    # oren
    for dx in (-12, 12):
        pygame.draw.ellipse(s, fur, pygame.Rect((50 + dx - 8) * u, 4 * u, 16 * u, 40 * u))
        pygame.draw.ellipse(s, inner, pygame.Rect((50 + dx - 4) * u, 11 * u, 8 * u, 27 * u))
    # lijfje
    pygame.draw.ellipse(s, fur, pygame.Rect(25 * u, 36 * u, 50 * u, 54 * u))
    # buikje
    pygame.draw.ellipse(s, inner, pygame.Rect(36 * u, 64 * u, 28 * u, 22 * u))
    # oogjes
    for dx in (-10, 10):
        pygame.draw.circle(s, ink, (int((50 + dx) * u), int(54 * u)), int(4 * u))
    # blosjes
    for dx in (-17, 17):
        pygame.draw.circle(s, (255, 130, 150), (int((50 + dx) * u), int(60 * u)), int(3.6 * u))
    # snorharen
    for side in (-1, 1):
        for i, dy in enumerate((-2, 3)):
            pygame.draw.line(s, rose, ((50 + side * 8) * u, (62 + dy) * u),
                             ((50 + side * 20) * u, (60 + dy * 1.8) * u), max(1, int(1.8 * u)))
    # neusje
    pygame.draw.polygon(s, rose, [(46 * u, 61 * u), (54 * u, 61 * u), (50 * u, 67 * u)])
    # mondje
    pygame.draw.arc(s, ink, pygame.Rect(44 * u, 65 * u, 6 * u, 6 * u),
                    math.pi * 1.0, math.pi * 2.0, max(1, int(1.8 * u)))
    pygame.draw.arc(s, ink, pygame.Rect(50 * u, 65 * u, 6 * u, 6 * u),
                    math.pi * 1.0, math.pi * 2.0, max(1, int(1.8 * u)))
    # voetjes
    for dx in (-11, 11):
        pygame.draw.ellipse(s, inner, pygame.Rect((50 + dx - 7) * u, 84 * u, 14 * u, 8 * u))
    return s


def make_nest(w: int) -> pygame.Surface:
    """Nestje/mandje waar een mama-dier in zit."""
    h = int(w * 0.42)
    ss = 3
    sw, sh = w * ss, h * ss
    s = pygame.Surface((sw, sh), pygame.SRCALPHA)
    brown, light, dark = (150, 104, 62), (192, 142, 88), (108, 72, 42)
    pygame.draw.ellipse(s, light, pygame.Rect(0, 0, sw, sh * 0.55))
    pygame.draw.ellipse(s, dark, pygame.Rect(sw * 0.07, sh * 0.10, sw * 0.86, sh * 0.38))
    pygame.draw.ellipse(s, brown, pygame.Rect(0, sh * 0.22, sw, sh * 0.78))
    # takjes-streepjes
    for i in range(5):
        x0 = sw * (0.06 + 0.17 * i)
        pygame.draw.arc(s, dark, pygame.Rect(x0, sh * 0.34, sw * 0.24, sh * 0.62),
                        math.pi * 0.15, math.pi * 0.85, max(2, 2 * ss))
    return pygame.transform.smoothscale(s, (w, h))


def make_heart(size: int, color=CORAL) -> pygame.Surface:
    return _supersample(lambda sz: _draw_heart(sz, color), size)


def _draw_heart(size: int, color) -> pygame.Surface:
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    pygame.draw.circle(s, color, (int(31 * u), int(34 * u)), int(22 * u))
    pygame.draw.circle(s, color, (int(69 * u), int(34 * u)), int(22 * u))
    pygame.draw.polygon(s, color, [(10 * u, 42 * u), (90 * u, 42 * u), (50 * u, 90 * u)])
    return s


def make_trace_icon(size: int) -> pygame.Surface:
    return _supersample(_draw_trace_icon, size)


def _draw_trace_icon(size: int) -> pygame.Surface:
    """Golfje met stipjes: menu-icoon voor het lijnen-volgen-spel."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    pts = [((12 + 76 * i / 40) * u, (50 - 20 * math.sin(i / 40 * math.tau * 0.75)) * u)
           for i in range(41)]
    pygame.draw.lines(s, (255, 255, 255), False, pts, max(2, int(5 * u)))
    for f in (0.0, 0.5, 1.0):
        x = (12 + 76 * f) * u
        y = (50 - 20 * math.sin(f * math.tau * 0.75)) * u
        pygame.draw.circle(s, AMBER, (int(x), int(y)), int(8 * u))
    return s


def make_hand_icon(size: int, color=AMBER) -> pygame.Surface:
    return _supersample(lambda sz: _draw_hand_icon(sz, color), size)


def _draw_hand_icon(size: int, color=AMBER) -> pygame.Surface:
    """Cartoon-zwaaihandje voor de 'Zwaai met je handen!'-uitnodiging."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    palm = pygame.Rect(30 * u, 42 * u, 40 * u, 44 * u)
    pygame.draw.ellipse(s, color, palm)
    fingers = [(34, 40, -14), (44, 40, -20), (54, 40, -20), (64, 42, -14)]
    for fx, fy, ln in fingers:
        pygame.draw.line(s, color, (fx * u, fy * u + 6 * u), (fx * u, (fy + ln) * u), int(9 * u))
        pygame.draw.circle(s, color, (int(fx * u), int((fy + ln) * u)), int(4.5 * u))
    pygame.draw.line(s, color, (30 * u, 58 * u), (16 * u, 48 * u), int(9 * u))  # duim
    pygame.draw.circle(s, color, (int(16 * u), int(48 * u)), int(4.5 * u))
    return s


def make_storm_cloud(w: int) -> pygame.Surface:
    return _supersample(_draw_storm_cloud, w)


def _draw_storm_cloud(size: int) -> pygame.Surface:
    """Knorrig onweerswolkje: obstakel in Vliegende draak, poft weg door drakenvuur."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    body = (108, 100, 158)
    dark = (82, 76, 126)
    ink = (35, 32, 58)
    # bliksemstaartje onder de wolk
    zig = [(50, 66), (43, 78), (51, 76), (44, 92)]
    pygame.draw.lines(s, AMBER, False, [(x * u, y * u) for x, y in zig], max(3, int(3.5 * u)))
    # bollen die samen de wolk vormen
    for cx, cy, r in [(28, 46, 20), (50, 36, 26), (72, 46, 20), (50, 52, 24)]:
        pygame.draw.circle(s, dark, (int(cx * u), int((cy + 3) * u)), int(r * u))
    for cx, cy, r in [(28, 44, 19), (50, 34, 25), (72, 44, 19), (50, 50, 23)]:
        pygame.draw.circle(s, body, (int(cx * u), int(cy * u)), int(r * u))
    # knorrig gezichtje: schuine wenkbrauwen, oogjes, pruilmondje
    for side in (-1, 1):
        ex = 50 + side * 11
        pygame.draw.line(s, ink, ((ex - side * 7) * u, 33 * u), ((ex + side * 5) * u, 37 * u),
                         max(2, int(2.6 * u)))
        pygame.draw.circle(s, (255, 255, 255), (int(ex * u), int(43 * u)), int(5.5 * u))
        pygame.draw.circle(s, ink, (int(ex * u), int(44 * u)), int(2.6 * u))
    pygame.draw.arc(s, ink, pygame.Rect(43 * u, 52 * u, 14 * u, 9 * u),
                    math.pi * 0.1, math.pi * 0.9, max(2, int(2.6 * u)))
    return s


def make_flower(size: int, color) -> pygame.Surface:
    return _supersample(lambda sz: _draw_flower(sz, color), size)


def _draw_flower(size: int, color) -> pygame.Surface:
    """Bloemkop met blaadjes en een blij gezichtje; de steel tekent SwayPlant zelf."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    ink = (35, 32, 58)
    for i in range(7):
        ang = i * math.tau / 7 - math.pi / 2
        px, py = 50 + math.cos(ang) * 30, 50 + math.sin(ang) * 30
        rect = pygame.Rect(0, 0, int(40 * u), int(26 * u))
        rect.center = (int(px * u), int(py * u))
        petal = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.ellipse(petal, color, petal.get_rect())
        rot = pygame.transform.rotozoom(petal, -math.degrees(ang), 1.0)
        s.blit(rot, rot.get_rect(center=rect.center))
    pygame.draw.circle(s, AMBER, (int(50 * u), int(50 * u)), int(17 * u))
    for dx in (-7, 7):
        pygame.draw.circle(s, ink, (int((50 + dx) * u), int(47 * u)), int(2.6 * u))
    pygame.draw.arc(s, ink, pygame.Rect(43 * u, 50 * u, 14 * u, 9 * u),
                    math.pi * 1.05, math.pi * 1.95, max(2, int(2.4 * u)))
    return s


def make_grass(size: int) -> pygame.Surface:
    return _supersample(_draw_grass, size)


def _draw_grass(size: int) -> pygame.Surface:
    """Grastoefje van een paar sprieten, om de bodem levend te maken."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    for i, (x0, tip, wgt) in enumerate([(30, 14, 9), (44, 8, 11), (58, 12, 10), (70, 22, 8)]):
        col = (150 + i * 12, 215, 100 + i * 10)
        bend = (i - 1.5) * 8
        pts = [(x0 * u, 100 * u),
               ((x0 + bend * 0.4) * u, (100 - (100 - tip) * 0.55) * u),
               ((x0 + bend) * u, tip * u)]
        pygame.draw.lines(s, col, False, pts, max(3, int(wgt * u * 0.9)))
    return s


def make_orb(radius: int, color) -> pygame.Surface:
    """Toverbal: dekkende snoepbal met glans en een blij gezichtje."""
    d = radius * 2
    y, x = np.ogrid[:d, :d]
    nx = (x - radius + 0.5) / radius
    ny = (y - radius + 0.5) / radius
    r = np.sqrt(nx ** 2 + ny ** 2)
    inside = r <= 1.0
    # bolvormige belichting: licht linksboven, donkere rand
    lit = np.clip(1.18 - 0.48 * np.sqrt((nx + 0.4) ** 2 + (ny + 0.4) ** 2), 0.55, 1.18)
    c = np.array(color, dtype=np.float64)
    rgba = np.zeros((d, d, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(c * lit[..., None], 0, 255).astype(np.uint8)
    rgba[..., 3] = np.where(inside, 255, 0).astype(np.uint8)
    surf = _surface_from_rgba(rgba)
    hl = pygame.Surface((d, d), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, int(radius * 0.55), int(radius * 0.34))
    rect.center = (int(radius * 0.62), int(radius * 0.55))
    pygame.draw.ellipse(hl, (255, 255, 255, 150), rect)
    surf.blit(hl, (0, 0))
    ink = (35, 32, 58)
    for side in (-1, 1):
        pygame.draw.circle(surf, ink, (int(radius + side * radius * 0.32),
                                       int(radius * 0.95)), max(2, int(radius * 0.08)))
    mond = pygame.Rect(0, 0, int(radius * 0.42), int(radius * 0.3))
    mond.center = (radius, int(radius * 1.22))
    pygame.draw.arc(surf, ink, mond, math.pi * 1.05, math.pi * 1.95, max(2, int(radius * 0.06)))
    return surf


def make_crystal(w: int, h: int, color) -> pygame.Surface:
    """Doorschijnend kristal om je achter te verstoppen (Kristalgrot)."""
    ss = 3
    sw, sh = w * ss, h * ss
    s = pygame.Surface((sw, sh), pygame.SRCALPHA)
    pts = [(0.5, 0.0), (0.92, 0.22), (0.80, 1.0), (0.20, 1.0), (0.08, 0.22)]
    poly = [(px * sw, py * sh) for px, py in pts]
    light = tuple(min(255, v + 70) for v in color)
    pygame.draw.polygon(s, (*color, 150), poly)
    pygame.draw.polygon(s, (*light, 210), poly, max(3, 3 * ss))
    # facetlijnen vanaf de punt
    for tx in (0.20, 0.50, 0.80):
        pygame.draw.line(s, (*light, 110), (0.5 * sw, 0), (tx * sw, sh), max(2, 2 * ss))
    # glimlicht
    pygame.draw.polygon(s, (255, 255, 255, 70),
                        [(0.42 * sw, 0.10 * sh), (0.55 * sw, 0.16 * sh),
                         (0.34 * sw, 0.72 * sh), (0.26 * sw, 0.62 * sh)])
    return pygame.transform.smoothscale(s, (w, h))


def make_key(size: int) -> pygame.Surface:
    return _supersample(_draw_key, size)


def _draw_key(size: int) -> pygame.Surface:
    """Gouden sleuteltje om te verzamelen in de Kristalgrot."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    gold, dark = (255, 205, 90), (200, 150, 50)
    pygame.draw.circle(s, gold, (int(50 * u), int(26 * u)), int(19 * u), int(10 * u))
    pygame.draw.line(s, gold, (50 * u, 44 * u), (50 * u, 88 * u), int(11 * u))
    for ty in (70, 84):
        pygame.draw.line(s, gold, (50 * u, ty * u), (68 * u, ty * u), int(9 * u))
    pygame.draw.circle(s, dark, (int(50 * u), int(26 * u)), int(19 * u), max(2, int(3 * u)))
    pygame.draw.circle(s, (255, 240, 190), (int(43 * u), int(19 * u)), int(4 * u))
    return s


def make_trophy(size: int, color=AMBER) -> pygame.Surface:
    return _supersample(lambda sz: _draw_trophy(sz, color), size)


def _draw_trophy(size: int, color) -> pygame.Surface:
    """Trofeebeker per avontuur, met een ster erop."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    dark = tuple(max(0, int(v * 0.65)) for v in color)
    # oren
    for side in (-1, 1):
        rect = pygame.Rect(0, 0, int(26 * u), int(34 * u))
        rect.center = (int((50 + side * 30) * u), int(32 * u))
        pygame.draw.arc(s, dark, rect, 0, math.tau, max(3, int(6 * u)))
    # kelk
    pygame.draw.rect(s, color, pygame.Rect(30 * u, 12 * u, 40 * u, 34 * u),
                     border_bottom_left_radius=int(20 * u), border_bottom_right_radius=int(20 * u))
    pygame.draw.ellipse(s, dark, pygame.Rect(30 * u, 8 * u, 40 * u, 10 * u))
    # steel + voet
    pygame.draw.rect(s, color, pygame.Rect(45 * u, 46 * u, 10 * u, 16 * u))
    pygame.draw.rect(s, dark, pygame.Rect(32 * u, 62 * u, 36 * u, 9 * u),
                     border_radius=int(4 * u))
    pygame.draw.rect(s, color, pygame.Rect(26 * u, 71 * u, 48 * u, 11 * u),
                     border_radius=int(5 * u))
    # ster op de kelk
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = (9 if i % 2 == 0 else 4) * u
        pts.append((50 * u + math.cos(ang) * rr, 29 * u + math.sin(ang) * rr))
    pygame.draw.polygon(s, (255, 250, 230), pts)
    return s


def make_lock(size: int) -> pygame.Surface:
    return _supersample(_draw_lock, size)


def _draw_lock(size: int) -> pygame.Surface:
    """Slotje voor nog niet vrijgespeelde avonturen."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    body, dark = (168, 172, 200), (108, 112, 142)
    rect = pygame.Rect(0, 0, int(30 * u), int(24 * u))
    rect.center = (int(50 * u), int(38 * u))
    pygame.draw.arc(s, dark, rect, 0, math.pi, max(3, int(7 * u)))
    pygame.draw.rect(s, body, pygame.Rect(30 * u, 44 * u, 40 * u, 34 * u),
                     border_radius=int(8 * u))
    pygame.draw.circle(s, dark, (int(50 * u), int(58 * u)), int(5 * u))
    pygame.draw.line(s, dark, (50 * u, 60 * u), (50 * u, 69 * u), max(2, int(4 * u)))
    return s


def make_cmd_icon(kind: str, size: int, color=AMBER) -> pygame.Surface:
    return _supersample(lambda sz: _draw_cmd_icon(kind, sz, color), size)


def _draw_cmd_icon(kind: str, size: int, color) -> pygame.Surface:
    """Simpele gebaar-pictogrammen voor Dans!: pijlen, handjes, zwaai-boogjes."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    u = size / 100.0
    w = max(4, int(10 * u))
    if kind in ("spring", "buk"):
        up = kind == "spring"
        y0, y1 = (78, 26) if up else (22, 74)
        pygame.draw.line(s, color, (50 * u, y0 * u), (50 * u, y1 * u), w)
        dy = 22 if up else -22
        for side in (-1, 1):
            pygame.draw.line(s, color, (50 * u, y1 * u),
                             ((50 + side * 20) * u, (y1 + dy) * u), w)
    elif kind == "klap":
        hand = _draw_hand_icon(int(size * 0.62), color)
        s.blit(pygame.transform.rotozoom(hand, -20, 1.0), (int(-4 * u), int(22 * u)))
        s.blit(pygame.transform.rotozoom(pygame.transform.flip(hand, True, False), 20, 1.0),
               (int(42 * u), int(22 * u)))
    elif kind == "zwaai":
        for i, ry in enumerate((36, 52, 68)):
            rect = pygame.Rect(14 * u, (ry - 12) * u, 72 * u, 30 * u)
            pygame.draw.arc(s, color, rect, math.pi * 0.15, math.pi * 0.85, max(3, int(6 * u)))
    else:  # "armen": twee armen omhoog in een V
        for side in (-1, 1):
            pygame.draw.line(s, color, (50 * u, 80 * u),
                             ((50 + side * 26) * u, 30 * u), w)
            pygame.draw.circle(s, color, (int((50 + side * 26) * u), int(26 * u)), int(7 * u))
    return s


def make_vignette(w: int, h: int) -> pygame.Surface:
    """Donkere ruimte-tint + vignet, één keer over het camerabeeld gelegd per frame."""
    small_w, small_h = w // 8, h // 8
    y, x = np.ogrid[:small_h, :small_w]
    nx = (x / small_w - 0.5) * 2
    ny = (y / small_h - 0.5) * 2
    r = np.sqrt(nx ** 2 + ny ** 2)
    a = np.clip(0.30 + 0.45 * np.clip(r - 0.55, 0, 1) ** 1.6, 0, 0.82) * 255
    rgba = np.zeros((small_h, small_w, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = VOID
    rgba[..., 3] = a.astype(np.uint8)
    small = _surface_from_rgba(rgba)
    return pygame.transform.smoothscale(small, (w, h))


def make_starfield(w: int, h: int, n: int = 90, seed: int = 7) -> pygame.Surface:
    """Subtiele vaste sterren in de donkere hoeken."""
    rng = np.random.default_rng(seed)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(n):
        x = rng.uniform(0, w)
        y = rng.uniform(0, h)
        # vooral in de randen laten leven, midden is voor het kind
        edge = min(x, w - x) / w + min(y, h - y) / h
        if rng.uniform() < edge * 2.2:
            continue
        r = rng.choice([1, 1, 1, 2])
        a = int(rng.uniform(60, 160))
        pygame.draw.circle(s, (255, 255, 255, a), (int(x), int(y)), r)
    return s
