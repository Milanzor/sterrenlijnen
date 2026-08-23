"""De lijfspellen (MediaPipe-pose, LeapMove-stijl): draak, toverballen,
kristalgrot, bellen hooghouden en dans.

Alle lijfspellen delen BodyMode: polsgloed, de uitnodiging als er niemand in
beeld staat, en het stop-gebaar (armen gekruist op je schouders = terug).
"""
import math
import random
import time

import pygame

import theme
from base import Mode
from entities import (AmbientBee, BounceBubble, Dragon, FallingOrb, FireBreath,
                      FlyingStar, KeyPickup, Particle, PopRing, ScrollStar,
                      StormCloud, SwayPlant)


class BodyMode(Mode):
    needs = "body"

    def __init__(self, game):
        super().__init__(game)
        self.body_seen_t = 0.0
        self.wrist_view: list[list[float]] = []  # gladgestreken polsposities
        self.head_view: list[float] | None = None
        self.exit_k = 0.0

    def poll_body(self):
        """→ (body, events, alive). Bij het stop-gebaar wisselt de modus en is alive False."""
        body = self.g.cam.get_body()
        events = self.g.cam.poll_body_events()
        if body.seen:
            self.body_seen_t = time.time()
        self.exit_k = body.exit_k if body.seen else 0.0
        if "exit" in events:
            self.g.sounds.bloop.play()
            self.g.go_back()
            return body, events, False
        return body, events, True

    def track_points(self, body, dt):
        """Polsen + hoofd soepel laten meelopen (detectie tikt maar op ~30 Hz)."""
        g = self.g
        k = 1 - math.exp(-dt * 14)
        pts = [list(g.to_screen(*wz)) for wz in body.wrists]
        if len(pts) != len(self.wrist_view):
            self.wrist_view = pts
        else:
            for cur, tgt in zip(self.wrist_view, pts):
                cur[0] += (tgt[0] - cur[0]) * k
                cur[1] += (tgt[1] - cur[1]) * k
        hx, hy = g.to_screen(*body.head)
        if self.head_view is None:
            self.head_view = [hx, hy]
        else:
            self.head_view[0] += (hx - self.head_view[0]) * k
            self.head_view[1] += (hy - self.head_view[1]) * k

    def touch_points(self) -> list:
        pts = [tuple(p) for p in self.wrist_view]
        if self.head_view is not None:
            pts.append(tuple(self.head_view))
        return pts

    def body_x(self) -> float | None:
        return self.head_view[0] if self.head_view else None

    def draw_body_feedback(self, s):
        g = self.g
        for wx, wy in self.wrist_view:
            s.blit(g.palm_glow, (wx - 44, wy - 44), special_flags=pygame.BLEND_ADD)
        if self.exit_k > 0.08:  # armen gekruist: vulring laat zien dat stoppen eraan komt
            rect = pygame.Rect(0, 0, 110, 110)
            rect.center = (g.W / 2, g.H * 0.16)
            pygame.draw.arc(s, theme.AMBER, rect, math.pi / 2 - self.exit_k * math.tau,
                            math.pi / 2, 9)
            txt = g.txt_stop
            s.blit(txt, (g.W / 2 - txt.get_width() / 2, rect.bottom + 8))

    def draw_invite_if_lost(self, s):
        if time.time() - self.body_seen_t > 2.5:
            self.g.draw_invite(s, text=self.g.txt_invite_body)


class DragonMode(BodyMode):
    label = "Vliegende draak"

    GRAVITY = 560.0
    LIFT = 1450.0    # volle klapwiek-energie wint ruim van de zwaartekracht
    GLIDE = 420.0    # armen omhoog houden = zachtjes zweven
    DIVE = 850.0     # bukken = duiken
    MAX_FALL, MAX_RISE = 540.0, 620.0

    def __init__(self, game):
        super().__init__(game)
        g = game
        self.dragon = Dragon(g.dragon_frames, g.W * 0.30, g.H * 0.45)
        self.clouds: list[StormCloud] = []
        self.pickups: list[ScrollStar] = []
        self.fires: list[FireBreath] = []
        self.bees: list[AmbientBee] = []
        self.plants = self._make_plants()
        self.cloud_timer = 3.0
        self.star_timer = 1.2
        self.bee_timer = random.uniform(4, 8)
        self.hint = theme.font(42, bold=True).render(
            "Klapwiek met je armen — klap in je handen voor vuur!", True, (255, 255, 255))

    def _make_plants(self):
        g = self.g
        plants, x = [], random.uniform(30, 80)
        while x < g.W - 30:
            if random.random() < 0.45:
                color = random.choice([theme.CORAL, theme.LILA, theme.ROSE, theme.SKY])
                plants.append(SwayPlant(x, g.H + 4, g.flower_sprites[color], flower=True,
                                        height=random.uniform(85, 150)))
            else:
                plants.append(SwayPlant(x, g.H + 4, random.choice(g.grass_sprites), flower=False))
            x += random.uniform(95, 170)
        return plants

    @property
    def scroll(self):
        return min(430.0, 235.0 + 28 * (self.level - 1))

    def update(self, dt):
        super().update(dt)
        g = self.g
        body, events, alive = self.poll_body()
        if not alive:
            return
        if body.seen:
            self._steer(body, dt)
            if "clap" in events:
                self._breathe_fire()
        else:
            # niemand in beeld: draak zweeft rustig in het midden
            self.dragon.lift = 0.0
            self.dragon.vy += (g.H * 0.45 - self.dragon.y) * 2.2 * dt - self.dragon.vy * 1.5 * dt

        d = self.dragon
        d.y += d.vy * dt
        top, bottom = g.H * 0.10 + d.radius, g.H * 0.94 - d.radius
        if d.y < top:
            d.y, d.vy = top, max(0.0, d.vy)
        elif d.y > bottom:
            d.y, d.vy = bottom, min(0.0, d.vy)
        d.update(dt)

        self._spawn(dt)
        self.clouds = [c for c in self.clouds if c.update(dt, self.scroll)]
        self.pickups = [p for p in self.pickups if p.update(dt, self.scroll)]
        self.fires = [f for f in self.fires if f.update(dt, g.W)]
        self.bees = [b for b in self.bees if b.update(dt)]
        for f in self.fires:  # vlammetje laat een spoor van vonkjes na
            if random.random() < 0.5:
                g.particles.append(Particle(
                    f.x - 20, f.y + random.uniform(-10, 10),
                    -random.uniform(60, 160), random.uniform(-50, 50),
                    random.uniform(0.2, 0.45), g.spark, gravity=0))
        self._collide()
        self._brush_plants(dt)

    def _steer(self, body, dt):
        g = self.g
        d = self.dragon
        tx = min(max(g.to_screen(body.x, 0)[0], g.W * 0.12), g.W * 0.62)
        d.x += (tx - d.x) * (1 - math.exp(-dt * 5.5))
        d.lift = body.lift
        accel = self.GRAVITY - self.LIFT * body.lift - (self.GLIDE if body.arms_up else 0.0)
        accel += self.DIVE * body.crouch
        d.vy = min(self.MAX_FALL, max(-self.MAX_RISE, d.vy + accel * dt))
        self.track_points(body, dt)

    def _breathe_fire(self):
        g = self.g
        d = self.dragon
        mx, my = d.x + d.radius * 1.6, d.y + d.radius * 0.1
        self.fires.append(FireBreath(mx, my, g.fire_glow))
        g.sounds.whoosh.play()
        for _ in range(8):
            g.particles.append(Particle(
                mx, my, random.uniform(120, 380), random.uniform(-120, 120),
                random.uniform(0.25, 0.5), g.droplets[theme.AMBER], gravity=0))

    def _spawn(self, dt):
        g = self.g
        self.cloud_timer -= dt
        if self.cloud_timer <= 0 and len(self.clouds) < min(3, 1 + self.level // 2):
            self.clouds.append(StormCloud(
                g.W + 120, random.uniform(g.H * 0.18, g.H * 0.62), g.cloud_sprite))
            self.cloud_timer = max(2.0, 4.2 - 0.25 * self.level) * random.uniform(0.75, 1.3)
        self.star_timer -= dt
        if self.star_timer <= 0 and len(self.pickups) < 9:
            y0 = random.uniform(g.H * 0.16, g.H * 0.72)
            arc = random.choice([-1, 0, 1]) * 55
            for i in range(3):  # boogje van drie sterren
                self.pickups.append(ScrollStar(
                    g.W + 60 + i * 105, y0 + math.sin(i / 2 * math.pi) * arc,
                    34, g.pickup_star))
            self.star_timer = random.uniform(1.6, 2.6)
        self.bee_timer -= dt
        if self.bee_timer <= 0 and len(self.bees) < 2:
            self.bees.append(AmbientBee(g.bee_frames, g.W, g.H))
            self.bee_timer = random.uniform(7, 14)

    def _collide(self):
        g = self.g
        d = self.dragon
        for p in self.pickups:
            if p.caught:
                continue
            if (p.x - d.x) ** 2 + (p.y - d.y) ** 2 < (p.radius + d.radius) ** 2:
                p.caught = True
                g.spawn_pop_effects(p.x, p.y, p.radius + 14, theme.AMBER)
                g.sounds.pop(pygame.time.get_ticks())
                g.flying.append(FlyingStar(p.x, p.y, g.hud_star_pos, g.star_fly))
                self.add_stars(1)
        for c in self.clouds:
            for f in self.fires:
                if (f.x - c.x) ** 2 + (f.y - c.y) ** 2 < (c.radius + 34) ** 2:
                    self._pop_cloud(c)
                    f.life = 0.0
                    break
            if not c.popped and c.bonk_t <= 0 and d.bump_t <= 0 \
                    and (c.x - d.x) ** 2 + (c.y - d.y) ** 2 < (c.radius + d.radius * 0.8) ** 2:
                # botsen mag: wolkje moppert even en duwt je weg, geen straf
                c.bonk_t, d.bump_t = 0.6, 0.7
                d.vy = math.copysign(300.0, d.y - c.y)
                g.sounds.boing.play()

    def _pop_cloud(self, c: StormCloud):
        g = self.g
        c.popped = True
        g.sounds.bloop.play()
        g.sounds.pop(pygame.time.get_ticks())
        g.spawn_pop_effects(c.x, c.y, c.radius, theme.LILA)
        for _ in range(10):
            col = random.choice(theme.PLAY_COLORS)
            g.particles.append(Particle(
                c.x, c.y, random.uniform(-320, 320), random.uniform(-420, -60),
                random.uniform(0.6, 1.1), g.confetti[col], gravity=650, additive=False))
        g.flying.append(FlyingStar(c.x, c.y, g.hud_star_pos, g.star_fly))
        self.add_stars(1)

    def _brush_plants(self, dt):
        d = self.dragon
        low = d.y > self.g.H * 0.72
        for pl in self.plants:
            pl.update(dt)
            if low and abs(pl.x - d.x) < 170:
                pl.push = math.copysign(min(0.55, abs(pl.push) + dt * 3), pl.x - d.x)
                if random.random() < dt * 3:  # dwarrelend blaadje
                    self.g.particles.append(Particle(
                        pl.x, self.g.H - 60, random.uniform(-40, 80), -random.uniform(60, 160),
                        random.uniform(0.5, 0.9), self.g.droplets[theme.LIME], gravity=160))

    def draw(self, s):
        for b in self.bees:
            b.draw(s)
        for pl in self.plants:
            pl.draw(s)
        for c in self.clouds:
            c.draw(s)
        for p in self.pickups:
            p.draw(s)
        for f in self.fires:
            f.draw(s)
        self.dragon.draw(s)
        self.draw_body_feedback(s)
        self.draw_invite_if_lost(s)
        super().draw(s)


class OrbsMode(BodyMode):
    """Toverballen: stap opzij en vang alleen de goede kleur met je handen of hoofd."""

    label = "Toverballen"
    CATCH_R = 82
    PER_COLOR = 6  # zoveel vangen, dan een nieuwe kleur

    COLOR_NAMES = [("ROOD", theme.CORAL), ("BLAUW", theme.SKY), ("GROEN", theme.LIME),
                   ("PAARS", theme.LILA), ("ROZE", theme.ROSE), ("GEEL", theme.AMBER)]

    def __init__(self, game):
        super().__init__(game)
        self.orbs: list[FallingOrb] = []
        self.spawn_timer = 1.0
        self.order = list(range(len(self.COLOR_NAMES)))
        random.shuffle(self.order)
        self.target_i = 0
        self.caught_this_color = 0
        self._set_target()
        self.hint = theme.font(42, bold=True).render(
            "Vang alleen de goede kleur!", True, (255, 255, 255))

    def _set_target(self):
        name, color = self.COLOR_NAMES[self.order[self.target_i % len(self.order)]]
        self.target_color = color
        self.banner = theme.font(64, bold=True).render(f"Vang {name}!", True, color)
        self.banner_orb = self.g.orb_sprites_small[color]

    def _next_target(self):
        self.target_i += 1
        if self.target_i % len(self.order) == 0:
            random.shuffle(self.order)
        self.caught_this_color = 0
        self._set_target()
        self.g.sounds.golden.play()

    def update(self, dt):
        super().update(dt)
        g = self.g
        body, events, alive = self.poll_body()
        if not alive:
            return
        if body.seen:
            self.track_points(body, dt)

        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.orbs) < min(7, 3 + self.level):
            # doelkleur valt het vaakst, zodat vangen altijd lukt
            if random.random() < 0.55:
                color = self.target_color
            else:
                color = random.choice([c for _, c in self.COLOR_NAMES if c != self.target_color])
            speed = random.uniform(120, 175) * min(1.9, 1 + 0.10 * (self.level - 1))
            self.orbs.append(FallingOrb(random.uniform(90, g.W - 90), 46, speed,
                                        color, g.orb_sprites[color]))
            self.spawn_timer = max(0.55, 1.5 - 0.09 * self.level) * random.uniform(0.7, 1.3)

        pts = self.touch_points() if body.seen else []
        for o in self.orbs:
            if o.state == FallingOrb.FALL and not o.caught:
                for px, py in pts:
                    if (px - o.x) ** 2 + (py - o.y) ** 2 < (self.CATCH_R + o.radius) ** 2:
                        self._touch(o, px)
                        break

        alive_orbs = []
        for o in self.orbs:
            if o.update(dt, g.H):
                alive_orbs.append(o)
            elif not o.caught and o.state == FallingOrb.FALL and o.color == self.target_color:
                g.sounds.fizzle.play()  # doelkleur gemist: dooft zachtjes, geen drama
        self.orbs = alive_orbs

    def _touch(self, o: FallingOrb, px: float):
        g = self.g
        if o.color == self.target_color:
            o.caught = True
            g.spawn_pop_effects(o.x, o.y, o.radius + 12, o.color)
            g.sounds.pop(pygame.time.get_ticks())
            g.flying.append(FlyingStar(o.x, o.y, g.hud_star_pos, g.star_fly))
            self.add_stars(1)
            self.caught_this_color += 1
            if self.caught_this_color >= self.PER_COLOR:
                self._next_target()
        else:
            o.reject(o.x - px if o.x != px else 1.0)
            g.sounds.boing.play()

    def draw(self, s):
        g = self.g
        for o in self.orbs:
            o.draw(s)
        # opdrachtbanner met voorbeeldbal en voortgangsstipjes
        bx = g.W / 2 - (self.banner.get_width() + 74) / 2
        by = g.H * 0.13
        s.blit(self.banner_orb, (bx, by - 6))
        s.blit(self.banner, (bx + 74, by))
        for i in range(self.PER_COLOR):
            col = self.target_color if i < self.caught_this_color else (90, 94, 132)
            pygame.draw.circle(s, col, (int(g.W / 2 - self.PER_COLOR * 14 + 14 + i * 28),
                                        int(by + 78)), 9)
        self.draw_body_feedback(s)
        self.draw_invite_if_lost(s)
        super().draw(s)


class CrystalMode(BodyMode):
    """Kristalgrot: pak sleutels in het donker, verstop je achter een kristal
    zodra het zoeklicht komt."""

    label = "Kristalgrot"
    DARK, WARN, SWEEP = range(3)
    KEY_R = 95
    HIDE_R = 145     # zo dicht bij een kristal tellen als 'verstopt'
    BEAM_HALF = 130

    def __init__(self, game):
        super().__init__(game)
        g = game
        self.crystal_x = [g.W * fx for fx in (0.18, 0.50, 0.82)]
        self.keys: list[KeyPickup] = []
        self.state = CrystalMode.DARK
        self.state_t = random.uniform(5.0, 7.0)
        self.sweep_dir = 1
        self.beam_x = -300.0
        self.spotted = False
        self.praise_t = 0.0
        self.hint = theme.font(42, bold=True).render(
            "Pak de sleutels — verstop je als het licht komt!", True, (255, 255, 255))

    def update(self, dt):
        super().update(dt)
        g = self.g
        body, events, alive = self.poll_body()
        if not alive:
            return
        if body.seen:
            self.track_points(body, dt)
        self.praise_t = max(0.0, self.praise_t - dt)

        for k in self.keys:
            k.update(dt)
        if self.state == CrystalMode.DARK:
            self._dark_phase(dt, body)
        elif self.state == CrystalMode.WARN:
            self.state_t -= dt
            if self.state_t <= 0:
                self.state = CrystalMode.SWEEP
                self.sweep_dir = -self.sweep_dir
                self.beam_x = -260.0 if self.sweep_dir > 0 else g.W + 260.0
                self.spotted = False
        else:
            self._sweep_phase(dt, body)

    def _dark_phase(self, dt, body):
        g = self.g
        self.state_t -= dt
        while len(self.keys) < 2:
            self.keys.append(KeyPickup(random.uniform(g.W * 0.10, g.W * 0.90),
                                       random.uniform(g.H * 0.40, g.H * 0.72), g.key_sprite))
        if body.seen:
            for k in self.keys:
                if k.collected or k.age < 0.4:
                    continue
                for px, py in self.touch_points():
                    if (px - k.x) ** 2 + (py - k.y) ** 2 < self.KEY_R ** 2:
                        k.collected = True
                        g.spawn_pop_effects(k.x, k.y, 58, theme.AMBER)
                        g.sounds.pop(pygame.time.get_ticks())
                        g.flying.append(FlyingStar(k.x, k.y, g.hud_star_pos, g.star_fly))
                        self.add_stars(1)
                        break
            self.keys = [k for k in self.keys if not k.collected]
        if self.state_t <= 0:
            self.state = CrystalMode.WARN
            self.state_t = 1.6
            self.g.sounds.peep.play()

    def _sweep_phase(self, dt, body):
        g = self.g
        speed = (g.W + 520) / max(2.2, 3.4 - 0.15 * (self.level - 1))
        self.beam_x += speed * dt * self.sweep_dir
        bx = self.body_x()
        if body.seen and bx is not None and abs(self.beam_x - bx) < self.BEAM_HALF:
            hidden = any(abs(bx - cx) < self.HIDE_R for cx in self.crystal_x)
            if not hidden and not self.spotted:
                self.spotted = True  # gezien! alleen een lachje, geen straf
                g.sounds.wheee.play()
        done = self.beam_x > g.W + 280 if self.sweep_dir > 0 else self.beam_x < -280
        if done:
            if body.seen and not self.spotted:
                # de hele zwaai onvindbaar gebleven: bonus!
                g.sounds.tada.play()
                self.praise_t = 1.6
                px = bx if bx is not None else g.W / 2
                g.spawn_pop_effects(px, g.H * 0.4, 90, theme.AMBER)
                for i in range(2):
                    g.flying.append(FlyingStar(px + i * 18, g.H * 0.4,
                                               g.hud_star_pos, g.star_fly))
                self.add_stars(2)
            self.state = CrystalMode.DARK
            self.state_t = max(3.5, random.uniform(5.0, 7.5) - 0.2 * self.level)

    def draw(self, s):
        g = self.g
        for k in self.keys:
            k.draw(s)
        if self.state == CrystalMode.WARN:
            # waarschuwing: pulserende gloed bovenin
            pulse = 0.5 + 0.5 * math.sin(self.t * 14)
            glow = g.warn_glow
            glow.set_alpha(int(90 + 120 * pulse))
            s.blit(glow, ((g.W - glow.get_width()) / 2, -glow.get_height() * 0.45))
            txt = g.txt_light_comes
            s.blit(txt, ((g.W - txt.get_width()) / 2, g.H * 0.20))
        elif self.state == CrystalMode.SWEEP:
            s.blit(g.beam_sprite, (self.beam_x - g.beam_sprite.get_width() / 2, -40),
                   special_flags=pygame.BLEND_ADD)
        # kristallen over het spiegelbeeld heen: daar verstop je je achter
        for cx, spr in zip(self.crystal_x, g.crystal_sprites):
            sway = math.sin(self.t * 0.8 + cx) * 4
            s.blit(spr, (cx - spr.get_width() / 2 + sway, g.H - spr.get_height() + 6))
        if self.praise_t > 0:
            txt = g.txt_well_hidden
            txt.set_alpha(int(255 * min(1.0, self.praise_t / 0.4)))
            s.blit(txt, ((g.W - txt.get_width()) / 2, g.H * 0.30))
            txt.set_alpha(255)
        self.draw_body_feedback(s)
        self.draw_invite_if_lost(s)
        super().draw(s)


class BounceMode(BodyMode):
    """Bellen hooghouden: stuit de bel met je handen of hoofd en tel mee tot vier."""

    label = "Bellen hooghouden"
    BOUNCES = 4
    TOUCH_R = 60

    def __init__(self, game):
        super().__init__(game)
        self.bubbles: list[BounceBubble] = []
        self._spawn_bubble()
        self.hint = theme.font(42, bold=True).render(
            "Houd de bel hoog — tel mee: 1, 2, 3, 4!", True, (255, 255, 255))

    def _spawn_bubble(self):
        g = self.g
        color = random.choice(list(g.bounce_sprites))
        self.bubbles.append(BounceBubble(
            random.uniform(g.W * 0.25, g.W * 0.75), -90, 85, color, g.bounce_sprites[color]))

    def update(self, dt):
        super().update(dt)
        g = self.g
        body, events, alive = self.poll_body()
        if not alive:
            return
        if body.seen:
            self.track_points(body, dt)
            if "clap" in events:  # klap = reddingszetje omhoog voor alle bellen
                for b in self.bubbles:
                    b.vy = min(b.vy, -400.0)
                g.sounds.whoosh.play()

        want = 2 if self.level >= 2 else 1
        while len(self.bubbles) < want:
            self._spawn_bubble()

        pts = self.touch_points() if body.seen else []
        keep = []
        for b in self.bubbles:
            b.update(dt, g.W)
            if b.hit_cooldown <= 0:
                for px, py in pts:
                    if (px - b.x) ** 2 + (py - b.y) ** 2 < (self.TOUCH_R + b.radius) ** 2:
                        b.bounce_up(px)
                        g.sounds.pop(pygame.time.get_ticks())
                        g.rings.append(PopRing(b.x, b.y + b.radius * 0.7, 40, b.color))
                        if b.count >= self.BOUNCES:
                            self._complete(b)
                        break
            if b.count < self.BOUNCES and b.y < g.H + b.radius:
                if b.y > g.H - b.radius * 0.4 and b.vy > 0:
                    # gemist: zachtjes uit, nieuwe bel — geen drama
                    g.sounds.fizzle.play()
                    for _ in range(6):
                        g.particles.append(Particle(
                            b.x + random.uniform(-20, 20), g.H - 16,
                            random.uniform(-70, 70), -random.uniform(40, 130),
                            random.uniform(0.3, 0.55), g.spark, gravity=220))
                    continue
                keep.append(b)
        self.bubbles = keep

    def _complete(self, b: BounceBubble):
        g = self.g
        g.sounds.tada.play()
        g.spawn_pop_effects(b.x, b.y, b.radius, b.color)
        for _ in range(10):
            col = random.choice(theme.PLAY_COLORS)
            g.particles.append(Particle(
                b.x, b.y, random.uniform(-300, 300), random.uniform(-420, -80),
                random.uniform(0.6, 1.1), g.confetti[col], gravity=650, additive=False))
        for i in range(2):
            g.flying.append(FlyingStar(b.x + i * 18, b.y, g.hud_star_pos, g.star_fly))
        self.add_stars(2)
        b.count = self.BOUNCES  # markeert 'm als klaar; hij wordt niet meer bewaard

    def draw(self, s):
        g = self.g
        for b in self.bubbles:
            digit = g.count_digits[min(b.count, self.BOUNCES)] if b.count > 0 else None
            b.draw(s, digit)
        self.draw_body_feedback(s)
        self.draw_invite_if_lost(s)
        super().draw(s)


class DanceMode(BodyMode):
    """Dans!: doe de beweging die de alien voordoet — springen, klappen, bukken,
    zwaaien of je armen omhoog."""

    label = "Dans!"
    SHOW, GO, HIT, MISS = range(4)

    CMDS = [
        ("spring", "Spring!"),
        ("klap", "Klap in je handen!"),
        ("buk", "Buk!"),
        ("zwaai", "Zwaai je armen!"),
        ("armen", "Armen omhoog!"),
    ]

    def __init__(self, game):
        super().__init__(game)
        self.state = DanceMode.SHOW
        self.state_t = 1.2
        self.cmd = None
        self.hold = 0.0
        self._next_cmd()
        self.hint = theme.font(42, bold=True).render(
            "Doe de beweging na!", True, (255, 255, 255))

    def _next_cmd(self):
        options = [c for c in self.CMDS if c is not self.cmd]
        self.cmd = random.choice(options)
        key, label = self.cmd
        color = random.choice(theme.PLAY_COLORS)
        self.cmd_txt = theme.font(78, bold=True).render(label, True, color)
        self.cmd_icon = self.g.cmd_icons[key]
        self.state = DanceMode.SHOW
        self.state_t = 1.2
        self.hold = 0.0
        self.g.sounds.peep.play()

    @property
    def window(self):
        return max(3.0, 5.2 - 0.3 * (self.level - 1))

    def update(self, dt):
        super().update(dt)
        body, events, alive = self.poll_body()
        if not alive:
            return
        if body.seen:
            self.track_points(body, dt)

        self.state_t -= dt
        if self.state == DanceMode.SHOW:
            if self.state_t <= 0:
                self.state = DanceMode.GO
                self.state_t = self.window
        elif self.state == DanceMode.GO:
            if body.seen and self._check(body, events, dt):
                self._success()
            elif self.state_t <= 0:
                self.state = DanceMode.MISS  # "bijna!" — gewoon door naar de volgende
                self.state_t = 1.1
                self.g.sounds.fizzle.play()
        elif self.state_t <= 0:  # HIT of MISS voorbij
            self._next_cmd()

    def _check(self, body, events, dt) -> bool:
        key = self.cmd[0]
        if key == "spring":
            return "jump" in events
        if key == "klap":
            return "clap" in events
        if key == "buk":
            self.hold = self.hold + dt if body.crouch > 0.5 else 0.0
            return self.hold >= 0.35
        if key == "zwaai":
            self.hold = self.hold + dt if body.lift > 0.4 else max(0.0, self.hold - dt)
            return self.hold >= 0.5
        # armen omhoog
        self.hold = self.hold + dt if body.arms_up else 0.0
        return self.hold >= 0.5

    def _success(self):
        g = self.g
        self.state = DanceMode.HIT
        self.state_t = 1.1
        g.sounds.tada.play()
        g.sounds.pop(pygame.time.get_ticks())
        cx, cy = g.W / 2, g.H * 0.42
        g.spawn_pop_effects(cx, cy, 110, theme.AMBER)
        for _ in range(8):
            col = random.choice(theme.PLAY_COLORS)
            g.particles.append(Particle(
                cx, cy, random.uniform(-320, 320), random.uniform(-420, -80),
                random.uniform(0.6, 1.1), g.confetti[col], gravity=650, additive=False))
        g.flying.append(FlyingStar(cx, cy, g.hud_star_pos, g.star_fly))
        self.add_stars(1)

    def draw(self, s):
        g = self.g
        # de alien danst voor: hupt op de maat, draait blij bij een hit
        bob = abs(math.sin(self.t * 4.5)) * 26
        spin = math.sin(self.t * 12) * 14 if self.state == DanceMode.HIT else \
            math.sin(self.t * 2.2) * 6
        alien = pygame.transform.rotozoom(g.alien_big, spin, 1.15)
        ax, ay = g.W * 0.16, g.H * 0.60
        s.blit(alien, (ax - alien.get_width() / 2, ay - alien.get_height() / 2 - bob))

        # opdracht: pictogram + tekst, met aflopende ring in de GO-fase
        icon = self.cmd_icon
        ix, iy = g.W / 2, g.H * 0.34
        if self.state == DanceMode.SHOW:
            k = 0.7 + 0.3 * min(1.0, (1.2 - self.state_t) / 0.3)
            icon = pygame.transform.rotozoom(icon, 0, k)
        s.blit(icon, (ix - icon.get_width() / 2, iy - icon.get_height() / 2))
        s.blit(self.cmd_txt, (ix - self.cmd_txt.get_width() / 2, iy + 110))
        if self.state == DanceMode.GO:
            k = self.state_t / self.window
            rect = pygame.Rect(0, 0, 240, 240)
            rect.center = (ix, iy)
            pygame.draw.arc(s, theme.AMBER, rect, math.pi / 2, math.pi / 2 + k * math.tau, 8)
        elif self.state == DanceMode.MISS:
            txt = g.txt_almost
            s.blit(txt, (ix - txt.get_width() / 2, iy + 190))
        self.draw_body_feedback(s)
        self.draw_invite_if_lost(s)
        super().draw(s)
