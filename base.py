"""Gedeelde basis voor alle spelmodi: constanten, HandCursor en Mode."""
import math
import random
import time

import pygame

import theme
from entities import Particle

TIP_HIT_R = 26     # ruime hitbox rond een vingertop, vergevingsgezind voor peuters
PALM_HIT_R = 38
SMOOTH_K = 22.0    # hoger = strakker volgen, lager = vloeiender
OPEN_HAND = 1.45   # openheid waarboven een hand als 'open' telt (vuist ≈ 1.1)
STARS_PER_LEVEL = 12

BUBBLE_RADII = [56, 64, 72, 80, 88]
MINI_RADII = [34, 42]
GIANT_R, GOLDEN_R, PASSENGER_R, DARTER_R = 118, 62, 92, 64
FALL_RADII = [36, 42, 48]
COMET_R = 30


class HandCursor:
    """Vloeiende 165 Hz-cursor bovenop de ~30 Hz-detectie."""

    def __init__(self, tips, palm):
        self.tips = [list(p) for p in tips]
        self.palm = list(palm)
        self.target_tips = tips
        self.target_palm = palm
        self.prev_tips = [list(p) for p in tips]
        self.open_k = 2.0
        self.target_open = 2.0
        self.last_seen = time.time()

    @property
    def is_open(self):
        return self.open_k > OPEN_HAND

    def set_target(self, tips, palm, openness):
        self.target_tips = tips
        self.target_palm = palm
        self.target_open = openness
        self.last_seen = time.time()

    def update(self, dt):
        k = 1 - math.exp(-dt * SMOOTH_K)
        self.prev_tips = [list(p) for p in self.tips]
        for p, t in zip(self.tips, self.target_tips):
            p[0] += (t[0] - p[0]) * k
            p[1] += (t[1] - p[1]) * k
        self.palm[0] += (self.target_palm[0] - self.palm[0]) * k
        self.palm[1] += (self.target_palm[1] - self.palm[1]) * k
        self.open_k += (self.target_open - self.open_k) * k


class Mode:
    label = ""
    show_score = True
    needs = "hands"  # welke tracking deze modus nodig heeft: "hands" of "body"

    def __init__(self, game):
        self.g = game
        self.stars = 0
        self.level = 1
        self.banner_t = 0.0
        self.t = 0.0
        self.hint = None  # (Surface, tot wanneer tonen)

    def add_stars(self, n=1):
        self.stars += n
        new_level = self.stars // STARS_PER_LEVEL + 1
        if new_level != self.level:
            self.level = new_level
            self.banner_t = 2.2
            self.g.sounds.fanfare.play()
            for _ in range(26):
                c = random.choice(theme.PLAY_COLORS)
                self.g.particles.append(Particle(
                    self.g.W / 2, self.g.H * 0.35,
                    random.uniform(-500, 500), random.uniform(-650, -150),
                    random.uniform(0.8, 1.5), self.g.confetti[c], gravity=700, additive=False))

    def update(self, dt):
        self.t += dt
        self.banner_t = max(0.0, self.banner_t - dt)

    def draw(self, s):
        if self.hint and self.t < 8:
            surf = self.hint
            surf.set_alpha(int(230 if self.t < 7 else 230 * (8 - self.t)))
            s.blit(surf, ((self.g.W - surf.get_width()) / 2, self.g.H * 0.86))
        if self.banner_t > 0:
            self._draw_level_banner(s)

    def _draw_level_banner(self, s):
        k = min(1.0, (2.2 - self.banner_t) / 0.25)
        alpha = 255 if self.banner_t > 0.5 else int(255 * self.banner_t / 0.5)
        txt = theme.font(96, bold=True).render(f"Level {self.level}!", True, theme.AMBER)
        txt = pygame.transform.rotozoom(txt, 0, 0.6 + 0.4 * k)
        txt.set_alpha(alpha)
        s.blit(txt, ((self.g.W - txt.get_width()) / 2, self.g.H * 0.28 - txt.get_height() / 2))
