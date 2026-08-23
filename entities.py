"""Spelobjecten: bellen (met gezichtjes), deeltjes, popringen, aliens, sterren."""
import math
import random
import time

import pygame

import theme


class Bubble:
    NORMAL, GIANT, GOLDEN, PASSENGER, DARTER = range(5)

    def __init__(self, kind: int, x: float, y: float, radius: int, color, sprite: pygame.Surface,
                 rise: float, mini: bool = False):
        self.kind = kind
        self.x, self.y = x, y
        self.radius = radius
        self.color = color
        self.sprite = sprite
        self.rise = rise
        self.mini = mini
        self.born = time.time()
        self.phase = random.uniform(0, math.tau)
        self.sway = random.uniform(24, 60)
        self.blink_at = time.time() + random.uniform(2, 6)
        self.blinking = 0.0
        self.vx = random.uniform(-30, 30) if mini else 0.0
        self.popped = False
        self.inner: pygame.Surface | None = None  # ster of alien ín de bel
        self.darts_left = 3          # schichtige bel wordt na drie sprongen moe
        self.dart_cooldown = 0.0

    def update(self, dt: float, speed_mul: float, w: float | None = None) -> None:
        self.y -= self.rise * speed_mul * dt
        self.phase += dt * 1.4
        self.x += math.sin(self.phase) * self.sway * dt * 0.6 + self.vx * dt
        self.vx *= 0.98 if self.kind != Bubble.DARTER else 0.96
        self.dart_cooldown = max(0.0, self.dart_cooldown - dt)
        if w is not None:  # stuiter van de schermranden
            if self.x < self.radius and self.vx < 0:
                self.x, self.vx = self.radius, -self.vx * 0.7
            elif self.x > w - self.radius and self.vx > 0:
                self.x, self.vx = w - self.radius, -self.vx * 0.7
        now = time.time()
        if now >= self.blink_at:
            self.blinking = 0.18
            self.blink_at = now + random.uniform(2.5, 7)
        self.blinking = max(0.0, self.blinking - dt)

    def draw(self, screen: pygame.Surface, look_at: tuple | None) -> None:
        r = self.radius
        bob = math.sin(self.phase * 2) * r * 0.03
        screen.blit(self.sprite, (self.x - self.sprite.get_width() / 2,
                                  self.y - self.sprite.get_height() / 2 + bob))
        if self.inner is not None:
            wob = math.sin(self.phase * 2.5) * 4
            screen.blit(self.inner, (self.x - self.inner.get_width() / 2 + wob,
                                     self.y - self.inner.get_height() / 2 + bob))
        if self.kind in (Bubble.GOLDEN, Bubble.PASSENGER) or self.mini:
            return
        self._draw_face(screen, self.x, self.y + bob, look_at)

    def _draw_face(self, screen: pygame.Surface, cx: float, cy: float, look_at: tuple | None) -> None:
        r = self.radius
        eye_dx = r * 0.34
        eye_w, eye_h = int(r * 0.30), int(r * 0.40)
        if self.kind == Bubble.GIANT:
            eye_w = int(eye_w * 1.15)
        # ogen kijken naar de dichtstbijzijnde hand — dat maakt ze levend
        lx, ly = 0.0, 0.0
        if look_at is not None:
            dx, dy = look_at[0] - cx, look_at[1] - cy
            d = math.hypot(dx, dy) or 1.0
            lx, ly = dx / d * r * 0.07, dy / d * r * 0.07
        for side in (-1, 1):
            ex, ey = cx + side * eye_dx, cy - r * 0.10
            if self.blinking > 0:
                pygame.draw.line(screen, (30, 30, 55), (ex - eye_w // 2, ey), (ex + eye_w // 2, ey), 3)
                continue
            rect = pygame.Rect(0, 0, eye_w, eye_h)
            rect.center = (ex, ey)
            pygame.draw.ellipse(screen, (255, 255, 255), rect)
            pygame.draw.circle(screen, (30, 30, 55), (int(ex + lx), int(ey + ly)), max(3, int(r * 0.085)))
        # blosjes
        for side in (-1, 1):
            pygame.draw.circle(screen, (255, 150, 150), (int(cx + side * r * 0.52), int(cy + r * 0.18)),
                               max(3, int(r * 0.09)))
        # schichtige bel kijkt ondeugend: schuine wenkbrauwtjes
        if self.kind == Bubble.DARTER and self.blinking <= 0:
            for side in (-1, 1):
                bx = cx + side * eye_dx
                by = cy - r * 0.38
                pygame.draw.line(screen, (60, 45, 80),
                                 (bx - side * eye_w * 0.5, by + r * 0.06),
                                 (bx + side * eye_w * 0.5, by), 4)
        # mond: verrast rondje bij de reus, anders een lach
        if self.kind == Bubble.GIANT:
            pygame.draw.circle(screen, (60, 45, 80), (int(cx), int(cy + r * 0.28)), max(4, int(r * 0.11)))
        else:
            rect = pygame.Rect(0, 0, int(r * 0.42), int(r * 0.30))
            rect.center = (int(cx), int(cy + r * 0.22))
            pygame.draw.arc(screen, (60, 45, 80), rect, math.pi * 1.05, math.pi * 1.95, 3)


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "sprite", "gravity", "additive")

    def __init__(self, x, y, vx, vy, life, sprite, gravity=380.0, additive=True):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.sprite = sprite
        self.gravity = gravity
        self.additive = additive

    def update(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0:
            return False
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return True

    def draw(self, screen: pygame.Surface) -> None:
        k = self.life / self.max_life
        if isinstance(self.sprite, list):  # helderheidstrapjes, dimt naar het einde
            spr = self.sprite[min(len(self.sprite) - 1, int(k * len(self.sprite)))]
            flags = pygame.BLEND_ADD if self.additive else 0
            screen.blit(spr, (self.x - spr.get_width() / 2, self.y - spr.get_height() / 2),
                        special_flags=flags)
            return
        spr = self.sprite
        if k < 0.5:
            spr.set_alpha(int(255 * k * 2))
        screen.blit(spr, (self.x - spr.get_width() / 2, self.y - spr.get_height() / 2))
        spr.set_alpha(255)  # sprite wordt gedeeld tussen deeltjes


class PopRing:
    __slots__ = ("x", "y", "r0", "color", "life", "max_life")

    def __init__(self, x, y, r0, color):
        self.x, self.y, self.r0, self.color = x, y, r0, color
        self.life = self.max_life = 0.30

    def update(self, dt: float) -> bool:
        self.life -= dt
        return self.life > 0

    def draw(self, screen: pygame.Surface) -> None:
        k = 1 - self.life / self.max_life
        r = int(self.r0 * (1 + k * 1.1))
        w = max(1, int(6 * (1 - k)))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), r, w)


class FlyingStar:
    """Ster die na een prik naar de teller vliegt."""
    __slots__ = ("x", "y", "sx", "sy", "tx", "ty", "t", "dur", "sprite")

    def __init__(self, x, y, target, sprite):
        self.sx, self.sy = x, y
        self.x, self.y = x, y
        self.tx, self.ty = target
        self.t = 0.0
        self.dur = 0.55
        self.sprite = sprite

    def update(self, dt: float) -> bool:
        self.t += dt
        k = min(1.0, self.t / self.dur)
        e = k * k * (3 - 2 * k)
        arc = math.sin(k * math.pi) * 80  # boogje omhoog, dat oogt speels
        self.x = self.sx + (self.tx - self.sx) * e
        self.y = self.sy + (self.ty - self.sy) * e - arc
        return k < 1.0

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self.sprite, (self.x - self.sprite.get_width() / 2,
                                  self.y - self.sprite.get_height() / 2))


class FallingStar:
    """Ster (of komeet) die naar beneden dwarrelt — vangen met een open hand."""

    def __init__(self, x, radius, speed, sprite, comet=False):
        self.x, self.y = x, -radius - 20
        self.radius = radius
        self.vy = speed
        self.sprite = sprite
        self.comet = comet
        self.phase = random.uniform(0, math.tau)
        self.sway = random.uniform(30, 80) * (0.4 if comet else 1.0)
        self.rot = random.uniform(0, 360)
        self.rot_v = random.uniform(-90, 90) * (2.2 if comet else 1.0)
        self.caught = False

    def update(self, dt: float, h: int) -> bool:
        """False zodra hij gevangen is of de grond raakt (afhandeling bij de caller)."""
        self.phase += dt * 1.6
        self.x += math.sin(self.phase) * self.sway * dt
        self.y += self.vy * dt
        self.rot += self.rot_v * dt
        return not self.caught and self.y < h - self.radius * 0.4

    def draw(self, screen: pygame.Surface) -> None:
        img = pygame.transform.rotozoom(self.sprite, self.rot, 1.0)
        screen.blit(img, (self.x - img.get_width() / 2, self.y - img.get_height() / 2))


class Critter:
    """Diertje-baby: hupt over de grond tot een hand hem oppakt en thuisbrengt."""

    WANDER, HELD, FALLING = range(3)

    def __init__(self, species, x, ground_y, sprite, sprite_flipped, vx):
        self.species = species
        self.x, self.y = x, ground_y
        self.ground_y = ground_y
        self.sprite, self.sprite_flipped = sprite, sprite_flipped
        self.vx = vx
        self.vy = 0.0
        self.phase = random.uniform(0, math.tau)
        self.state = Critter.WANDER
        self.holder = None  # HandCursor die hem vasthoudt
        self.peep_at = time.time() + random.uniform(2.0, 6.0)

    def update(self, dt: float, w: float) -> None:
        self.phase += dt * 8.0
        if self.state == Critter.WANDER:
            self.x += self.vx * dt
            if self.x < 70 and self.vx < 0:
                self.vx = abs(self.vx)
            elif self.x > w - 70 and self.vx > 0:
                self.vx = -abs(self.vx)
            self.y = self.ground_y - abs(math.sin(self.phase)) * 14  # huppelpasjes
        elif self.state == Critter.FALLING:
            self.vy += 1400 * dt
            self.y += self.vy * dt
            if self.y >= self.ground_y:
                self.y, self.vy = self.ground_y, 0.0
                self.state = Critter.WANDER

    def follow(self, palm, dt: float) -> None:
        """In een hand: zachtjes onder de handpalm bungelen."""
        k = 1 - math.exp(-dt * 15)
        self.x += (palm[0] + math.sin(self.phase * 0.9) * 7 - self.x) * k
        self.y += (palm[1] + 54 - self.y) * k

    def drop(self) -> None:
        self.state = Critter.FALLING
        self.holder = None
        self.vy = 0.0

    def draw(self, screen: pygame.Surface) -> None:
        if self.state == Critter.HELD:
            img = pygame.transform.rotozoom(self.sprite, math.sin(self.phase) * 9, 1.0)
        else:
            img = self.sprite_flipped if self.vx < 0 else self.sprite
        screen.blit(img, (self.x - img.get_width() / 2, self.y - img.get_height() / 2))


class ParentAnimal:
    """Mama-dier in een nest; stuitert blij bij een hereniging, schudt bij het verkeerde kindje."""

    def __init__(self, species, x, y, sprite, nest):
        self.species = species
        self.x, self.y = x, y
        self.sprite, self.nest = sprite, nest
        self.phase = random.uniform(0, math.tau)
        self.bounce_t = 0.0
        self.shake_t = 0.0
        self.shake_cooldown = 0.0

    def update(self, dt: float) -> None:
        self.phase += dt * 1.8
        self.bounce_t = max(0.0, self.bounce_t - dt)
        self.shake_t = max(0.0, self.shake_t - dt)
        self.shake_cooldown = max(0.0, self.shake_cooldown - dt)

    def draw(self, screen: pygame.Surface) -> None:
        bob = math.sin(self.phase) * 5
        jump = math.sin((0.7 - self.bounce_t) / 0.7 * math.pi) * 34 if self.bounce_t > 0 else 0
        xoff = math.sin(self.shake_t * 26) * 10 if self.shake_t > 0 else 0
        img = self.sprite
        screen.blit(img, (self.x - img.get_width() / 2 + xoff,
                          self.y - img.get_height() / 2 + bob - jump))
        screen.blit(self.nest, (self.x - self.nest.get_width() / 2,
                                self.y + img.get_height() * 0.16))


class PeekAlien:
    """Alien die vanaf de onderrand komt gluren — tik hem op zijn hoofd."""

    RISE, HOLD, SINK, BOPPED = range(4)

    def __init__(self, x, bottom, sprite, peek, hold):
        self.x, self.bottom = x, bottom
        self.sprite = sprite
        self.h = sprite.get_height()
        self.peek = peek        # welk deel van de alien boven de rand uitkomt
        self.hold = hold        # hoelang hij blijft gluren
        self.k = 0.0            # 0 = verstopt, 1 = maximaal zichtbaar
        self.state = PeekAlien.RISE
        self.phase = random.uniform(0, math.tau)

    @property
    def top(self):
        return self.bottom - self.k * self.peek * self.h

    def update(self, dt: float) -> bool:
        self.phase += dt * 6
        if self.state == PeekAlien.RISE:
            self.k = min(1.0, self.k + dt / 0.3)
            if self.k >= 1.0:
                self.state = PeekAlien.HOLD
        elif self.state == PeekAlien.HOLD:
            self.hold -= dt
            if self.hold <= 0:
                self.state = PeekAlien.SINK
        elif self.state == PeekAlien.SINK:
            self.k -= dt / 0.45
        else:  # BOPPED: snel weer naar beneden
            self.k -= dt / 0.2
        return self.k > 0

    def hit_test(self, px: float, py: float) -> bool:
        return abs(px - self.x) < 64 and self.top - 14 < py < self.bottom

    def draw(self, screen: pygame.Surface) -> None:
        wob = math.sin(self.phase) * 4
        screen.blit(self.sprite, (self.x - self.sprite.get_width() / 2 + wob, self.top))


class Dragon:
    """De draak uit Vliegende draak: klapwiekt mee met het kind (CC0-sprite).

    De physics (lift, zwaartekracht) zit in de spelmodus; hier alleen animatie:
    vleugeltempo schaalt met de klapwiek-energie en de neus kantelt met de
    verticale snelheid mee.
    """

    def __init__(self, frames: list, x: float, y: float):
        self.frames = frames
        self.x, self.y = x, y
        self.vy = 0.0
        self.anim_t = random.uniform(0, 10)
        self.lift = 0.0
        self.bump_t = 0.0  # net tegen een wolkje gebotst: even knipperen

    @property
    def radius(self) -> float:
        return self.frames[0].get_height() * 0.34

    def update(self, dt: float) -> None:
        self.anim_t += dt * (5 + self.lift * 13)
        self.bump_t = max(0.0, self.bump_t - dt)

    def draw(self, screen: pygame.Surface) -> None:
        img = self.frames[int(self.anim_t) % len(self.frames)]
        tilt = max(-24.0, min(24.0, -self.vy * 0.045))
        img = pygame.transform.rotozoom(img, tilt, 1.0)
        if self.bump_t > 0 and int(self.bump_t * 18) % 2 == 0:
            img.set_alpha(140)
        screen.blit(img, (self.x - img.get_width() / 2, self.y - img.get_height() / 2))
        img.set_alpha(255)


class StormCloud:
    """Knorrig onweerswolkje dat voorbijdrijft; drakenvuur poft hem weg."""

    def __init__(self, x: float, y: float, sprite: pygame.Surface):
        self.x, self.y = x, y
        self.sprite = sprite
        self.radius = sprite.get_width() * 0.34
        self.phase = random.uniform(0, math.tau)
        self.bonk_t = 0.0     # draak botste ertegen: even schudden
        self.popped = False

    def update(self, dt: float, scroll: float) -> bool:
        self.x -= scroll * dt
        self.phase += dt * 2.2
        self.bonk_t = max(0.0, self.bonk_t - dt)
        return not self.popped and self.x > -self.sprite.get_width()

    def draw(self, screen: pygame.Surface) -> None:
        bob = math.sin(self.phase) * 7
        shake = math.sin(self.bonk_t * 30) * 12 if self.bonk_t > 0 else 0
        screen.blit(self.sprite, (self.x - self.sprite.get_width() / 2 + shake,
                                  self.y - self.sprite.get_height() / 2 + bob))


class FireBreath:
    """Vuurpufje dat na een klap in je handen uit de drakenmond vooruit schiet."""

    SPEED = 760.0

    def __init__(self, x: float, y: float, glow_levels: list):
        self.x, self.y = x, y
        self.glow = glow_levels
        self.life = self.max_life = 1.1
        self.phase = random.uniform(0, math.tau)

    def update(self, dt: float, w: float) -> bool:
        self.x += self.SPEED * dt
        self.phase += dt * 20
        self.y += math.sin(self.phase) * 30 * dt
        self.life -= dt
        return self.life > 0 and self.x < w + 60

    def draw(self, screen: pygame.Surface) -> None:
        k = self.life / self.max_life
        spr = self.glow[min(len(self.glow) - 1, int(k * len(self.glow)))]
        screen.blit(spr, (self.x - spr.get_width() / 2, self.y - spr.get_height() / 2),
                    special_flags=pygame.BLEND_ADD)


class FallingOrb:
    """Toverbal die naar beneden dwarrelt; alleen de doelkleur wil gevangen worden."""

    FALL, REJECT = range(2)

    def __init__(self, x: float, radius: int, speed: float, color, sprite: pygame.Surface):
        self.x, self.y = x, -radius - 20
        self.radius = radius
        self.color = color
        self.sprite = sprite
        self.vy = speed
        self.vx = 0.0
        self.phase = random.uniform(0, math.tau)
        self.sway = random.uniform(25, 60)
        self.rot = 0.0
        self.rot_v = 0.0
        self.state = FallingOrb.FALL
        self.caught = False

    def reject(self, away: float) -> None:
        """Verkeerde kleur aangeraakt: stuitert lachend weg, geen straf."""
        self.state = FallingOrb.REJECT
        self.vx = math.copysign(random.uniform(320, 460), away)
        self.vy = -random.uniform(260, 380)
        self.rot_v = math.copysign(random.uniform(200, 340), away)

    def update(self, dt: float, h: int) -> bool:
        self.phase += dt * 1.7
        if self.state == FallingOrb.FALL:
            self.x += math.sin(self.phase) * self.sway * dt
            self.y += self.vy * dt
        else:
            self.vy += 900 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.rot += self.rot_v * dt
        return not self.caught and self.y < h + self.radius * 2

    def draw(self, screen: pygame.Surface) -> None:
        img = self.sprite
        if self.state == FallingOrb.REJECT:
            img = pygame.transform.rotozoom(img, self.rot, 1.0)
        screen.blit(img, (self.x - img.get_width() / 2, self.y - img.get_height() / 2))


class BounceBubble:
    """Grote bel om hoog te houden met je handen en hoofd — tel de stuiten mee!"""

    GRAVITY = 190.0

    def __init__(self, x: float, y: float, radius: int, color, sprite: pygame.Surface):
        self.x, self.y = x, y
        self.radius = radius
        self.color = color
        self.sprite = sprite
        self.vx = random.uniform(-60, 60)
        self.vy = 0.0
        self.count = 0        # hoe vaak al gestuit (het telgetal op de bel)
        self.hit_cooldown = 0.0
        self.phase = random.uniform(0, math.tau)

    def update(self, dt: float, w: float) -> None:
        self.phase += dt * 1.8
        self.vy += self.GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.hit_cooldown = max(0.0, self.hit_cooldown - dt)
        if self.x < self.radius and self.vx < 0:
            self.x, self.vx = self.radius, -self.vx * 0.85
        elif self.x > w - self.radius and self.vx > 0:
            self.x, self.vx = w - self.radius, -self.vx * 0.85

    def bounce_up(self, from_x: float) -> None:
        self.vy = -random.uniform(380, 460)
        self.vx = self.vx * 0.4 + (self.x - from_x) * 3.2
        self.count += 1
        self.hit_cooldown = 0.35

    def draw(self, screen: pygame.Surface, digit: pygame.Surface | None) -> None:
        bob = math.sin(self.phase * 2) * 3
        screen.blit(self.sprite, (self.x - self.sprite.get_width() / 2,
                                  self.y - self.sprite.get_height() / 2 + bob))
        if digit is not None:
            screen.blit(digit, (self.x - digit.get_width() / 2,
                                self.y - digit.get_height() / 2 + bob))


class KeyPickup:
    """Sleuteltje in de Kristalgrot: pak het als het zoeklicht uit is."""

    def __init__(self, x: float, y: float, sprite: pygame.Surface):
        self.x, self.y = x, y
        self.sprite = sprite
        self.phase = random.uniform(0, math.tau)
        self.age = 0.0
        self.collected = False

    def update(self, dt: float) -> None:
        self.phase += dt * 2.4
        self.age += dt

    def draw(self, screen: pygame.Surface) -> None:
        k = min(1.0, self.age / 0.35)  # even ingroeien
        img = self.sprite if k >= 1.0 else pygame.transform.rotozoom(self.sprite, 0, k)
        bob = math.sin(self.phase) * 8
        screen.blit(img, (self.x - img.get_width() / 2, self.y - img.get_height() / 2 + bob))


class ScrollStar:
    """Ster die in Vliegende draak van rechts aan komt drijven — vang hem met de draak."""

    def __init__(self, x: float, y: float, radius: int, sprite: pygame.Surface):
        self.x, self.y = x, y
        self.radius = radius
        self.sprite = sprite
        self.phase = random.uniform(0, math.tau)
        self.rot = random.uniform(0, 360)
        self.caught = False

    def update(self, dt: float, scroll: float) -> bool:
        self.x -= scroll * dt
        self.phase += dt * 2.0
        self.rot += 40 * dt
        return not self.caught and self.x > -self.radius * 2

    def draw(self, screen: pygame.Surface) -> None:
        img = pygame.transform.rotozoom(self.sprite, self.rot, 1.0)
        y = self.y + math.sin(self.phase) * 10
        screen.blit(img, (self.x - img.get_width() / 2, y - img.get_height() / 2))


class AmbientBee:
    """Bijtje dat af en toe zoemend voorbijvliegt — puur sfeer (CC0-sprite)."""

    def __init__(self, frames: list, w: float, h: float):
        self.frames = frames
        self.from_left = random.random() < 0.5
        span = frames[0].get_width()
        self.x = -span if self.from_left else w + span
        self.vx = random.uniform(130, 200) * (1 if self.from_left else -1)
        self.base_y = random.uniform(h * 0.18, h * 0.55)
        self.phase = random.uniform(0, math.tau)
        self.anim_t = 0.0
        self.w = w

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.phase += dt * 2.6
        self.anim_t += dt * 26  # vleugeltjes zoemen snel
        span = self.frames[0].get_width()
        return -span * 2 < self.x < self.w + span * 2

    def draw(self, screen: pygame.Surface) -> None:
        img = self.frames[int(self.anim_t) % len(self.frames)]
        if self.from_left:  # sprite kijkt van zichzelf naar links
            img = pygame.transform.flip(img, True, False)
        y = self.base_y + math.sin(self.phase) * 26
        screen.blit(img, (self.x - img.get_width() / 2, y - img.get_height() / 2))


class SwayPlant:
    """Bloem of grastoefje onderin: wuift in de wind en buigt weg als de draak
    er laag overheen scheert."""

    def __init__(self, x: float, ground_y: float, sprite: pygame.Surface,
                 flower: bool, height: float = 0.0):
        self.x, self.ground_y = x, ground_y
        self.sprite = sprite
        self.flower = flower
        self.height = height  # steellengte (alleen bloemen)
        self.phase = random.uniform(0, math.tau)
        self.sway_speed = random.uniform(1.1, 1.7)
        self.push = 0.0       # extra buiging door de draak, ebt weg

    def update(self, dt: float) -> None:
        self.phase += dt * self.sway_speed
        self.push *= math.exp(-dt * 2.4)

    def draw(self, screen: pygame.Surface) -> None:
        bend = math.sin(self.phase) * 0.08 + self.push
        if not self.flower:
            img = pygame.transform.rotozoom(self.sprite, -math.degrees(bend) * 0.5, 1.0)
            screen.blit(img, (self.x - img.get_width() / 2,
                              self.ground_y - img.get_height() + 6))
            return
        # steel als boogje richting de bloemkop
        top = (self.x + math.sin(bend) * self.height, self.ground_y - self.height)
        mid = (self.x + math.sin(bend) * self.height * 0.35, self.ground_y - self.height * 0.55)
        pygame.draw.lines(screen, (96, 176, 88), False,
                          [(self.x, self.ground_y), mid, top], 5)
        img = pygame.transform.rotozoom(self.sprite, -math.degrees(bend) * 0.7, 1.0)
        screen.blit(img, (top[0] - img.get_width() / 2, top[1] - img.get_height() / 2))


class EscapingAlien:
    """Passagier die uit zijn bel vliegt en zwaaiend het beeld uit tolt."""

    def __init__(self, x, y, sprite):
        self.x, self.y = x, y
        self.vx = random.choice([-1, 1]) * random.uniform(260, 420)
        self.vy = -random.uniform(350, 520)
        self.rot = 0.0
        self.rot_v = random.uniform(-220, 220)
        self.sprite = sprite
        self.t = 0.0

    def update(self, dt: float, h: int) -> bool:
        self.t += dt
        self.vy += 300 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rot += self.rot_v * dt
        return self.t < 4.0 and self.y < h + 200

    def draw(self, screen: pygame.Surface) -> None:
        wig = math.sin(self.t * 9) * 14  # zwaai-wiebel
        img = pygame.transform.rotozoom(self.sprite, self.rot + wig, 1.0)
        screen.blit(img, (self.x - img.get_width() / 2, self.y - img.get_height() / 2))
