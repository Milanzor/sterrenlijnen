"""De vijf handspellen: bellen, sterren, mama, aliens en lijnen volgen."""
import math
import random
import time

import pygame

import theme
from base import (BUBBLE_RADII, COMET_R, DARTER_R, FALL_RADII, GIANT_R,
                  GOLDEN_R, MINI_RADII, PALM_HIT_R, PASSENGER_R, TIP_HIT_R,
                  Mode)
from entities import (Bubble, Critter, EscapingAlien, FallingStar, FlyingStar,
                      ParentAnimal, Particle, PeekAlien, PopRing)


class BubblesMode(Mode):
    label = "Bellen prikken"
    music = "bellen"

    def __init__(self, game):
        super().__init__(game)
        self.bubbles: list[Bubble] = []
        self.cascade: list[tuple[float, Bubble]] = []
        self.spawn_timer = 0.8
        self.hint = theme.font(42, bold=True).render(
            "Prik de bellen met je vingers!", True, (255, 255, 255))

    # -------- spawnen

    def spawn_bubble(self):
        g = self.g
        roll = random.random()
        color = random.choice(theme.PLAY_COLORS)
        if roll < 0.06:
            kind, r, color = Bubble.GOLDEN, GOLDEN_R, theme.AMBER
        elif roll < 0.16 and self.level >= 2:
            kind, r = Bubble.GIANT, GIANT_R
        elif roll < 0.28 and self.level >= 2:
            kind, r = Bubble.DARTER, DARTER_R
        elif roll < 0.38:
            kind, r = Bubble.PASSENGER, PASSENGER_R
        else:
            kind, r = Bubble.NORMAL, random.choice(BUBBLE_RADII)
        x = random.uniform(r + 30, g.W - r - 30)
        rise = random.uniform(85, 130) + (25 if kind == Bubble.GOLDEN else 0)
        b = Bubble(kind, x, g.H + r + 10, r, color, g.bubble_sprites[(color, r)], rise)
        if kind == Bubble.GOLDEN:
            b.inner = g.star_inner
        elif kind == Bubble.PASSENGER:
            b.inner = g.alien_inner
        self.bubbles.append(b)

    def spawn_minis(self, parent: Bubble):
        for i in range(5):
            r = random.choice(MINI_RADII)
            b = Bubble(Bubble.NORMAL, parent.x, parent.y, r, parent.color,
                       self.g.bubble_sprites[(parent.color, r)],
                       random.uniform(95, 140), mini=True)
            ang = math.tau * i / 5 + random.uniform(-0.3, 0.3)
            b.vx = math.cos(ang) * 240
            b.y += math.sin(ang) * parent.radius * 0.4
            self.bubbles.append(b)

    # -------- poppen

    def pop(self, b: Bubble):
        if b.popped:
            return
        b.popped = True
        g = self.g
        g.spawn_pop_effects(b.x, b.y, b.radius, b.color, small=b.mini)
        g.flying.append(FlyingStar(b.x, b.y, g.hud_star_pos, g.star_fly))

        if b.kind == Bubble.GIANT:
            g.sounds.bloop.play()
            self.spawn_minis(b)
        elif b.kind == Bubble.GOLDEN:
            g.sounds.golden.play()
            others = [o for o in self.bubbles if o is not b and not o.popped]
            others.sort(key=lambda o: math.hypot(o.x - b.x, o.y - b.y))
            now = time.time()
            self.cascade += [(now + 0.09 * (i + 1), o) for i, o in enumerate(others)]
        elif b.kind == Bubble.PASSENGER:
            g.sounds.wheee.play()
            g.aliens.append(EscapingAlien(b.x, b.y, g.alien_big))
        g.sounds.pop(pygame.time.get_ticks())
        self.add_stars(1)

    # -------- logica

    def update(self, dt):
        super().update(dt)
        g = self.g
        self.spawn_timer -= dt
        interval = max(0.45, 1.15 - self.level * 0.08)
        max_bubbles = min(14, 7 + self.level)
        if self.spawn_timer <= 0 and sum(not b.popped for b in self.bubbles) < max_bubbles:
            self.spawn_bubble()
            self.spawn_timer = interval * random.uniform(0.7, 1.3)

        speed_mul = min(2.2, 1 + 0.12 * (self.level - 1))
        for b in self.bubbles:
            b.update(dt, speed_mul, g.W)
        self.bubbles = [b for b in self.bubbles if not b.popped and b.y > -b.radius - 40]

        self._flee_from_hands()

        now = time.time()
        due = [item for item in self.cascade if item[0] <= now]
        self.cascade = [item for item in self.cascade if item[0] > now]
        for _, b in due:
            self.pop(b)
        self._check_hits()

    def _flee_from_hands(self):
        """Schichtige bellen schieten opzij zodra een hand dichtbij komt."""
        for b in self.bubbles:
            if b.kind != Bubble.DARTER or b.darts_left <= 0 or b.dart_cooldown > 0:
                continue
            for c in self.g.cursors:
                dx = b.x - c.palm[0]
                dy = b.y - c.palm[1]
                if dx * dx + dy * dy < 190 ** 2:
                    b.vx = math.copysign(random.uniform(420, 560), dx if dx else 1)
                    b.dart_cooldown = 0.8
                    b.darts_left -= 1
                    self.g.sounds.boing.play()
                    break

    def _check_hits(self):
        for c in self.g.cursors:
            pts = [(p, TIP_HIT_R) for p in c.tips] + [(c.palm, PALM_HIT_R)]
            # ook het midden van de vingerbeweging checken, anders vlieg je door een bel heen
            for prev, cur in zip(c.prev_tips, c.tips):
                pts.append((((prev[0] + cur[0]) / 2, (prev[1] + cur[1]) / 2), TIP_HIT_R))
            for b in self.bubbles:
                if b.popped:
                    continue
                for (px, py), pr in pts:
                    if (px - b.x) ** 2 + (py - b.y) ** 2 < (pr + b.radius * 0.9) ** 2:
                        self.pop(b)
                        break

    def draw(self, s):
        g = self.g
        look = g.cursors[0].palm if g.cursors else None
        for b in self.bubbles:
            near = look
            if len(g.cursors) > 1:
                near = min((c.palm for c in g.cursors),
                           key=lambda p: (p[0] - b.x) ** 2 + (p[1] - b.y) ** 2)
            b.draw(s, near)
        super().draw(s)


class CatchMode(Mode):
    label = "Sterren vangen"
    music = "vangen"

    def __init__(self, game):
        super().__init__(game)
        self.stars_falling: list[FallingStar] = []
        self.spawn_timer = 1.0
        self.hint = theme.font(42, bold=True).render(
            "Vang de sterren met een open hand!", True, (255, 255, 255))

    def update(self, dt):
        super().update(dt)
        g = self.g
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.stars_falling) < min(9, 4 + self.level):
            comet = self.level >= 2 and random.random() < 0.15
            r = COMET_R if comet else random.choice(FALL_RADII)
            speed = random.uniform(160, 230) * min(2.0, 1 + 0.10 * (self.level - 1))
            self.stars_falling.append(FallingStar(
                random.uniform(r + 40, g.W - r - 40), r,
                speed * (1.8 if comet else 1.0),
                g.comet_sprite if comet else g.fall_sprites[r], comet=comet))
            self.spawn_timer = max(0.45, 1.5 - self.level * 0.1) * random.uniform(0.7, 1.3)

        for st in self.stars_falling:
            if st.comet and random.random() < 0.6:  # staartje
                g.particles.append(Particle(
                    st.x + random.uniform(-6, 6), st.y - st.radius * 0.5,
                    random.uniform(-25, 25), -random.uniform(40, 120),
                    random.uniform(0.3, 0.6), g.droplets[theme.SKY], gravity=-30))
            self._try_catch(st)

        alive = []
        for st in self.stars_falling:
            if st.update(dt, g.H):
                alive.append(st)
            elif not st.caught:  # zachtjes uitgedoofd op de grond, geen drama
                g.sounds.fizzle.play()
                for _ in range(6):
                    g.particles.append(Particle(
                        st.x + random.uniform(-14, 14), g.H - 12,
                        random.uniform(-60, 60), -random.uniform(30, 110),
                        random.uniform(0.3, 0.55), g.spark, gravity=200))
        self.stars_falling = alive

    def _try_catch(self, st: FallingStar):
        if st.caught:
            return
        g = self.g
        for c in g.cursors:
            if not c.is_open:
                continue
            dx = c.palm[0] - st.x
            dy = c.palm[1] - st.y
            if dx * dx + dy * dy < (st.radius + 55) ** 2:
                st.caught = True
                worth = 2 if st.comet else 1
                color = theme.SKY if st.comet else theme.AMBER
                g.spawn_pop_effects(st.x, st.y, st.radius + 16, color)
                g.sounds.pop(pygame.time.get_ticks())
                for i in range(worth):
                    g.flying.append(FlyingStar(st.x + i * 18, st.y, g.hud_star_pos, g.star_fly))
                if st.comet:
                    g.sounds.pop(pygame.time.get_ticks() + 1)
                self.add_stars(worth)
                return

    def draw(self, s):
        g = self.g
        for st in self.stars_falling:
            st.draw(s)
        # vangnet-affordance: open hand krijgt een ring, zo snappen kinderen het verschil
        for c in g.cursors:
            if c.is_open:
                pygame.draw.circle(s, theme.AMBER, (int(c.palm[0]), int(c.palm[1])), 62, 3)
        super().draw(s)


class AnimalsMode(Mode):
    label = "Naar mama!"
    music = "mama"

    PICKUP_R = 95    # hand-tot-diertje: oppakken gaat vanzelf, geen grijpgebaar nodig
    NEST_R = 155     # diertje-tot-mama: afleveren

    def __init__(self, game):
        super().__init__(game)
        g = game
        self.hint = theme.font(42, bold=True).render(
            "Breng de kleintjes naar hun mama!", True, (255, 255, 255))
        self.parents = [
            ParentAnimal(i, g.W * fx, g.H * 0.26, g.animal_parent[i], g.nest_sprite)
            for i, fx in enumerate((0.18, 0.50, 0.82))
        ]
        self.critters: list[Critter] = []
        self.ground_y = g.H - g.animal_baby[0][0].get_height() / 2 - 26
        self.spawn_timer = 0.4

    def spawn_critter(self):
        g = self.g
        species = random.randrange(len(self.parents))
        from_left = random.random() < 0.5
        spr, flipped = g.animal_baby[species]
        self.critters.append(Critter(
            species, -50 if from_left else g.W + 50, self.ground_y, spr, flipped,
            vx=random.uniform(45, 75) * (1 if from_left else -1)))

    def update(self, dt):
        super().update(dt)
        g = self.g
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.critters) < min(4, 1 + self.level):
            self.spawn_critter()
            self.spawn_timer = random.uniform(1.2, 2.4)

        for p in self.parents:
            p.update(dt)
        now = time.time()
        for c in self.critters:
            if c.state == Critter.HELD:
                if c.holder not in g.cursors:  # hand kwijt: diertje dwarrelt terug omlaag
                    c.drop()
                else:
                    c.follow(c.holder.palm, dt)
            elif c.state == Critter.WANDER and now >= c.peep_at:
                g.sounds.peep.play()
                c.peep_at = now + random.uniform(3.0, 8.0)
            c.update(dt, g.W)
        self._pickups()
        self._deliveries()

    def _pickups(self):
        g = self.g
        busy = {id(c.holder) for c in self.critters if c.state == Critter.HELD}
        for cur in g.cursors:
            if id(cur) in busy:  # één diertje per hand
                continue
            for c in self.critters:
                if c.state == Critter.HELD:
                    continue
                dx = cur.palm[0] - c.x
                dy = cur.palm[1] - c.y
                if dx * dx + dy * dy < self.PICKUP_R ** 2:
                    c.state = Critter.HELD
                    c.holder = cur
                    busy.add(id(cur))
                    g.sounds.peep.play()
                    g.rings.append(PopRing(c.x, c.y, 46, theme.AMBER))
                    break

    def _deliveries(self):
        g = self.g
        for c in list(self.critters):
            if c.state != Critter.HELD:
                continue
            for p in self.parents:
                dx, dy = c.x - p.x, c.y - p.y
                if dx * dx + dy * dy > self.NEST_R ** 2:
                    continue
                if p.species == c.species:
                    self._deliver(c, p)
                elif p.shake_cooldown <= 0:  # verkeerde mama schudt van nee, zonder drama
                    p.shake_t, p.shake_cooldown = 0.5, 1.4
                    g.sounds.boing.play()
                break

    def _deliver(self, c: Critter, p: ParentAnimal):
        g = self.g
        self.critters.remove(c)
        p.bounce_t = 0.7
        g.sounds.tada.play()
        g.sounds.pop(pygame.time.get_ticks())
        for _ in range(9):  # hartjes zweven omhoog
            g.particles.append(Particle(
                p.x + random.uniform(-40, 40), p.y + random.uniform(-30, 10),
                random.uniform(-60, 60), -random.uniform(90, 220),
                random.uniform(0.7, 1.2), g.heart_sprite, gravity=-90, additive=False))
        for i in range(2):
            g.flying.append(FlyingStar(p.x + i * 18, p.y, g.hud_star_pos, g.star_fly))
        self.add_stars(2)
        self.spawn_timer = min(self.spawn_timer, 0.9)

    def draw(self, s):
        held_species = {c.species for c in self.critters if c.state == Critter.HELD}
        for p in self.parents:
            if p.species in held_species:  # wijs de weg: pulserende ring om de juiste mama
                rr = int(self.NEST_R + math.sin(self.t * 4) * 8)
                pygame.draw.circle(s, theme.AMBER, (int(p.x), int(p.y)), rr, 3)
            p.draw(s)
        for c in sorted(self.critters, key=lambda c: c.state == Critter.HELD):
            c.draw(s)
        super().draw(s)


class WhackMode(Mode):
    label = "Aliens tikken"
    music = "aliens"

    def __init__(self, game):
        super().__init__(game)
        self.peekers: list[PeekAlien] = []
        self.spawn_timer = 0.7
        self.hint = theme.font(42, bold=True).render(
            "Tik de aliens op hun hoofd!", True, (255, 255, 255))

    def update(self, dt):
        super().update(dt)
        g = self.g
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.peekers) < min(5, 1 + self.level):
            slots = [g.W * (i + 1) / 7 for i in range(6)]
            free = [x for x in slots if all(abs(a.x - x) > 110 for a in self.peekers)]
            if free:
                hold = random.uniform(1.1, 2.0) * max(0.55, 1 - 0.08 * (self.level - 1))
                self.peekers.append(PeekAlien(random.choice(free), g.H, g.alien_peek,
                                              random.uniform(0.5, 0.9), hold))
            self.spawn_timer = max(0.35, 0.9 - 0.06 * self.level) * random.uniform(0.7, 1.3)
        self.peekers = [a for a in self.peekers if a.update(dt)]
        self._check_hits()

    def _check_hits(self):
        for c in self.g.cursors:
            pts = list(c.tips)
            for prev, cur in zip(c.prev_tips, c.tips):
                pts.append(((prev[0] + cur[0]) / 2, (prev[1] + cur[1]) / 2))
            for a in self.peekers:
                if a.state == PeekAlien.BOPPED or a.k < 0.3:
                    continue
                if any(a.hit_test(px, py) for px, py in pts):
                    self.bop(a)

    def bop(self, a: PeekAlien):
        g = self.g
        a.state = PeekAlien.BOPPED
        g.sounds.wheee.play()
        g.sounds.pop(pygame.time.get_ticks())
        g.spawn_pop_effects(a.x, a.top + 46, 70, theme.LIME)
        g.flying.append(FlyingStar(a.x, a.top + 30, g.hud_star_pos, g.star_fly))
        self.add_stars(1)

    def draw(self, s):
        for a in self.peekers:
            a.draw(s)
        super().draw(s)


def _arc(a0, a1, n, cx, cy, rx, ry):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / (n - 1)),
             cy + ry * math.sin(a0 + (a1 - a0) * i / (n - 1))) for i in range(n)]


def _star_points(n, r_in):
    """Stercontour met n punten (buiten- en binnenhoeken om en om), gesloten."""
    pts = []
    for i in range(2 * n + 1):
        ang = -math.pi / 2 + i * math.pi / n
        rr = 1.0 if i % 2 == 0 else r_in
        pts.append((math.cos(ang) * rr, math.sin(ang) * rr))
    return pts


def _trace_shapes():
    """Figuren om te volgen, per moeilijkheidslaag, in willekeurige eenheden.

    Alle figuren zijn één doorlopende lijn (kruisen mag, terugtekenen niet) en
    gebruiken schermcoördinaten: kleinere y is hoger.
    """
    star5 = [(math.cos(-math.pi / 2 + i * math.tau / 5),
              math.sin(-math.pi / 2 + i * math.tau / 5)) for i in range(5)]
    heart = []
    for i in range(61):
        t = math.tau * i / 60
        heart.append((16 * math.sin(t) ** 3,
                      -(13 * math.cos(t) - 5 * math.cos(2 * t)
                        - 2 * math.cos(3 * t) - math.cos(4 * t))))
    # wassende maan: buitenboog + holle binnenboog die elkaar in de punten raken
    maan = (_arc(0.890, math.tau - 0.890, 44, 0.5, 0.5, 0.5, 0.5)
            + _arc(-1.332, 1.332 - math.tau, 28, 0.72, 0.5, 0.40, 0.40))
    # wolk: platte onderkant met drie bollingen erbovenop
    wolk = ([(1, 0.72), (0, 0.72)]
            + _arc(math.pi, 0, 16, 0.16, 0.72, 0.16, -0.14)
            + _arc(math.pi, 0, 20, 0.50, 0.72, 0.18, -0.24)
            + _arc(math.pi, 0, 16, 0.84, 0.72, 0.16, -0.14))
    # vis: rug over de kop naar de staart, staartpunt, en over de buik terug
    vis = (_arc(math.pi, 0, 26, 0.4, 0.5, 0.4, -0.28)
           + [(1.0, 0.30), (1.0, 0.70), (0.8, 0.5)]
           + _arc(0, math.pi, 26, 0.4, 0.5, 0.4, 0.28))
    # bloem: golvende cirkel met zes bloemblaadjes
    bloem = [((0.82 + 0.18 * math.sin(6 * math.tau * i / 120)) * math.cos(math.tau * i / 120),
              (0.82 + 0.18 * math.sin(6 * math.tau * i / 120)) * math.sin(math.tau * i / 120))
             for i in range(121)]
    # slak: spiraal van binnen naar buiten
    slak = [((0.15 + 0.85 * i / 150) * math.cos(2.5 * math.tau * i / 150),
             (0.15 + 0.85 * i / 150) * math.sin(2.5 * math.tau * i / 150))
            for i in range(151)]
    return [
        [  # laag 1: losse halen
            ("lijn", [(0, 0), (1, 0)]),
            ("regenboog", _arc(math.pi, 0, 48, 0.5, 0, 0.5, -0.62)),
            ("golf", [(i / 48, 0.30 * math.sin(i / 48 * math.tau * 1.5)) for i in range(49)]),
            ("berg", [(0, 1), (0.25, 0), (0.5, 1), (0.75, 0), (1, 1)]),
        ],
        [  # laag 2: gesloten basisvormen
            ("vierkant", [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
            ("driehoek", [(0, 1), (0.5, 0), (1, 1), (0, 1)]),
            ("cirkel", _arc(-math.pi / 2, math.tau - math.pi / 2, 60, 0.5, 0.5, 0.5, 0.5)),
            ("vlieger", [(0.5, 0), (0.85, 0.5), (0.5, 1), (0.15, 0.5), (0.5, 0)]),
        ],
        [  # laag 3: herkenbare plaatjes
            ("maan", maan),
            ("huisje", [(0, 1), (0, 0.4), (0.5, 0), (1, 0.4), (1, 1), (0, 1)]),
            ("ster", [star5[i] for i in (0, 2, 4, 1, 3, 0)]),  # zoals kinderen hem tekenen
            ("bliksem", [(0.65, 0), (0.25, 0.5), (0.55, 0.5), (0.15, 1)]),
        ],
        [  # laag 4
            ("hart", heart),
            ("kroon", [(0, 1), (0, 0.35), (0.25, 0.65), (0.5, 0.25),
                       (0.75, 0.65), (1, 0.35), (1, 1), (0, 1)]),
            ("raket", [(0.35, 1), (0.35, 0.35), (0.5, 0), (0.65, 0.35), (0.65, 1), (0.35, 1)]),
            ("ijsje", [(0.30, 0.45), (0.5, 1), (0.70, 0.45), (0.78, 0.45)]  # hoorntje + randje
                      + _arc(0, math.pi, 24, 0.5, 0.45, 0.28, -0.34)
                      + [(0.30, 0.45)]),
        ],
        [  # laag 5
            ("wolk", wolk),
            ("acht", [(0.5 + 0.5 * math.cos(math.tau * i / 60),
                       0.5 + 0.28 * math.sin(2 * math.tau * i / 60)) for i in range(61)]),
            ("vis", vis),
            ("bloem", bloem),
        ],
        [  # laag 6: lange halen
            ("slak", slak),
            ("zon", _star_points(8, 0.62)),
        ],
    ]


def _resample(pts, spacing):
    """Zet een polyline om in punten op gelijke afstand langs de lijn."""
    out = [pts[0]]
    acc = 0.0
    x0, y0 = pts[0]
    for x1, y1 in pts[1:]:
        seg = math.hypot(x1 - x0, y1 - y0)
        while seg > 0 and acc + seg >= spacing:
            t = (spacing - acc) / seg
            x0, y0 = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            seg = math.hypot(x1 - x0, y1 - y0)
            acc = 0.0
            out.append((x0, y0))
        acc += seg
        x0, y0 = x1, y1
    return out


class TraceMode(Mode):
    label = "Lijnen volgen"
    music = "lijnen"

    HIT_R = 62       # ruim: de vinger hoeft maar ongeveer over de stip
    AHEAD = 3        # hoeveel stipjes je vooruit mag springen (tegen wild zwaaien)
    DOT_SPACING = 80

    def __init__(self, game):
        super().__init__(game)
        self.tiers = _trace_shapes()
        self.queue: list = []
        self._refill(first=True)
        self.done_t = 0.0
        self.hint = theme.font(42, bold=True).render(
            "Volg de stipjes met je vinger!", True, (255, 255, 255))
        self._new_shape()

    def _refill(self, first=False):
        """Vul de wachtrij: eerst laag voor laag (geschud per laag), daarna alles door elkaar."""
        if first:
            for tier in self.tiers:
                batch = tier[:]
                random.shuffle(batch)
                self.queue += batch
        else:
            batch = [shape for tier in self.tiers for shape in tier]
            random.shuffle(batch)
            self.queue += batch

    def _new_shape(self):
        g = self.g
        if not self.queue:
            self._refill()
        name, pts = self.queue.pop(0)
        self.shape_name = name
        # passend maken in een kader midden op het scherm, met behoud van verhoudingen
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w = max(xs) - min(xs) or 1.0
        h = max(ys) - min(ys) or 1.0
        k = min(g.W * 0.62 / w, g.H * 0.50 / h)
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        fitted = [((x - cx) * k + g.W / 2, (y - cy) * k + g.H * 0.55) for x, y in pts]
        self.dots = _resample(fitted, self.DOT_SPACING)
        self.lit = [False] * len(self.dots)
        self.lit_at = [0.0] * len(self.dots)
        self.progress = 0
        self.color = random.choice(theme.PLAY_COLORS)
        self.dot_glow = theme.make_glow(24, self.color, peak=210)
        self.name_txt = theme.font(48, bold=True).render(name, True, self.color)

    def update(self, dt):
        super().update(dt)
        g = self.g
        if self.done_t > 0:
            self.done_t -= dt
            if self.done_t <= 0:
                self._new_shape()
            return

        pts = []
        for c in g.cursors:
            pts += list(c.tips)
            for prev, cur in zip(c.prev_tips, c.tips):
                pts.append(((prev[0] + cur[0]) / 2, (prev[1] + cur[1]) / 2))
        for i in range(self.progress, min(self.progress + 1 + self.AHEAD, len(self.dots))):
            if self.lit[i]:
                continue
            dx_, dy_ = self.dots[i]
            if any((px - dx_) ** 2 + (py - dy_) ** 2 < self.HIT_R ** 2 for px, py in pts):
                self.lit[i] = True
                self.lit_at[i] = self.t
                g.sounds.pop(pygame.time.get_ticks())
                for _ in range(3):
                    g.particles.append(Particle(
                        dx_, dy_, random.uniform(-90, 90), random.uniform(-140, -30),
                        random.uniform(0.3, 0.55), g.droplets[self.color]))
        while self.progress < len(self.dots) and self.lit[self.progress]:
            self.progress += 1
        if self.progress == len(self.dots):
            self._complete()

    def _complete(self):
        g = self.g
        g.sounds.tada.play()
        for x, y in self.dots:
            c = random.choice(theme.PLAY_COLORS)
            g.particles.append(Particle(
                x, y, random.uniform(-220, 220), random.uniform(-420, -120),
                random.uniform(0.7, 1.3), g.confetti[c], gravity=700, additive=False))
        lx, ly = self.dots[-1]
        for i in range(3):
            g.flying.append(FlyingStar(lx + i * 18, ly, g.hud_star_pos, g.star_fly))
        self.add_stars(3)
        self.done_t = 1.4

    def draw(self, s):
        g = self.g
        # de hele figuur vaag als voorbeeld, het gevolgde stuk helder
        if len(self.dots) > 1:
            pygame.draw.lines(s, (80, 84, 122), False, self.dots, 3)
        if self.progress >= 2:
            pygame.draw.lines(s, self.color, False, self.dots[:self.progress], 6)
        for i, (x, y) in enumerate(self.dots):
            if self.lit[i]:
                s.blit(self.dot_glow, (x - 24, y - 24), special_flags=pygame.BLEND_ADD)
                r = 9 + 7 * max(0.0, 0.35 - (self.t - self.lit_at[i])) / 0.35
                pygame.draw.circle(s, (255, 255, 255), (int(x), int(y)), int(r))
            else:
                pygame.draw.circle(s, (205, 209, 238), (int(x), int(y)), 9, 2)
        # markeer de volgende stip met een draaiend sterretje
        if self.done_t <= 0 and self.progress < len(self.dots):
            x, y = self.dots[self.progress]
            rr = 26 + math.sin(self.t * 5) * 5
            pygame.draw.circle(s, theme.AMBER, (int(x), int(y)), int(rr), 3)
            star = pygame.transform.rotozoom(g.star_fly, self.t * 60, 1.0)
            s.blit(star, (x - star.get_width() / 2, y - star.get_height() / 2))
        s.blit(self.name_txt, ((g.W - self.name_txt.get_width()) / 2, g.H * 0.13))
        super().draw(s)
