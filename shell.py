"""De schil om de spellen heen, à la LeapMove: profielkeuze, hoofdmenu,
Avontuur (etappes met een trofee als beloning), Vrij spelen en de trofeeënkast.

Alle menu's werken hetzelfde als vanouds: hand op een bel houden tot de ring
vol is. ESC gaat één niveau terug; in lijfspellen kan dat ook met de armen
gekruist op je schouders.
"""
import math
import random
import time

import pygame

import profiles
import theme
from base import Mode
from entities import Particle
from modes_body import BounceMode, CrystalMode, DanceMode, DragonMode, OrbsMode
from modes_hand import (AnimalsMode, BubblesMode, CatchMode, TraceMode,
                        WhackMode)

# Avonturen: naam, kleur, etappes (spel + sterrendoel). Elk avontuur klaar = trofee.
ADVENTURES = [
    ("Sterrenweide", theme.AMBER, [(BubblesMode, 8), (CatchMode, 8)]),
    ("Bloemenvallei", theme.LIME, [(AnimalsMode, 8), (DragonMode, 8)]),
    ("Kristalgrot", theme.LILA, [(CrystalMode, 8), (TraceMode, 6)]),
    ("Wolkenland", theme.SKY, [(BounceMode, 8), (WhackMode, 8)]),
    ("Feestplaneet", theme.ROSE, [(DanceMode, 8), (OrbsMode, 8)]),
]

# Vrij spelen: alle tien de spellen. (klasse, belkleur, icoon-attribuut op Game)
FREE_GAMES = [
    (BubblesMode, theme.TEAL, "freeplay_bubble_icon", "Bellen prikken"),
    (CatchMode, theme.CORAL, "menu_star_icon", "Sterren vangen"),
    (AnimalsMode, theme.LILA, "menu_chick_icon", "Naar mama!"),
    (WhackMode, theme.SKY, "alien_inner", "Aliens tikken"),
    (TraceMode, theme.LIME, "menu_trace_icon", "Lijnen volgen"),
    (DragonMode, theme.ROSE, "menu_dragon_icon", "Vliegende draak"),
    (OrbsMode, theme.CORAL, "orb_icon", "Toverballen"),
    (CrystalMode, theme.LILA, "crystal_icon", "Kristalgrot"),
    (BounceMode, theme.SKY, "bounce_icon", "Hooghouden"),
    (DanceMode, theme.TEAL, "dance_icon", "Dans!"),
]


class HoverMenu:
    """Keuzebellen: hand erop houden tot de ring vol is."""

    HOLD = 1.1

    def __init__(self, options):
        # optie: {pos, r, sprite, icon, label, payload, enabled=True, badge=None}
        self.options = options
        for opt in self.options:
            opt.setdefault("enabled", True)
            opt.setdefault("badge", None)
            opt["hold"] = 0.0

    def update(self, game, dt):
        for opt in self.options:
            if not opt["enabled"]:
                continue
            ox, oy = opt["pos"]
            inside = any(
                (c.palm[0] - ox) ** 2 + (c.palm[1] - oy) ** 2 < opt["r"] ** 2
                or any((t[0] - ox) ** 2 + (t[1] - oy) ** 2 < opt["r"] ** 2 for t in c.tips)
                for c in game.cursors)
            if inside:
                opt["hold"] += dt
                if opt["hold"] >= self.HOLD:
                    game.sounds.golden.play()
                    game.spawn_pop_effects(ox, oy, opt["r"], theme.AMBER)
                    return opt["payload"]
            else:
                opt["hold"] = max(0.0, opt["hold"] - dt * 2)
        return None

    def draw(self, s, g):
        t = time.time()
        for i, opt in enumerate(self.options):
            ox, oy = opt["pos"]
            bob = math.sin(t * 1.6 + i * 2.1) * 8 if opt["enabled"] else 0
            for spr in (opt["sprite"], opt["icon"]):
                if spr is None:
                    continue
                if not opt["enabled"]:
                    spr.set_alpha(80)
                s.blit(spr, (ox - spr.get_width() / 2, oy - spr.get_height() / 2 + bob))
                spr.set_alpha(255)
            if opt["badge"] is not None:
                b = opt["badge"]
                s.blit(b, (ox - b.get_width() / 2, oy - b.get_height() / 2 + bob))
            txt = opt["label"]
            if txt is not None:
                if not opt["enabled"]:
                    txt.set_alpha(110)
                lx = min(max(10, ox - txt.get_width() / 2), g.W - txt.get_width() - 10)
                s.blit(txt, (lx, oy + opt["r"] + 20 + bob))
                txt.set_alpha(255)
            if opt["hold"] > 0:
                k = min(1.0, opt["hold"] / self.HOLD)
                rect = pygame.Rect(0, 0, opt["r"] * 2 + 26, opt["r"] * 2 + 26)
                rect.center = (ox, oy + bob)
                pygame.draw.arc(s, theme.AMBER, rect, math.pi / 2 - k * math.tau,
                                math.pi / 2, 8)


class ProfileMenu(Mode):
    label = "Wie speelt er?"
    show_score = False

    def __init__(self, game):
        super().__init__(game)
        g = game
        opts = []
        for i, (name, color) in enumerate(profiles.STARS):
            p = g.profiles_data["profiles"][i]
            sub = theme.font(28).render(
                f"{p['total_stars']} sterren · {p['adv_done']} trofee"
                + ("ën" if p["adv_done"] != 1 else ""), True, (215, 219, 248))
            opts.append({"pos": (g.W * (0.25 + 0.25 * i), g.H * 0.55), "r": 120,
                         "sprite": g.menu_bubbles_big[color],
                         "icon": g.profile_star_icons[i], "payload": i,
                         "label": theme.font(36, bold=True).render(name, True, (255, 255, 255)),
                         "badge": None, "sub": sub})
        self.menu = HoverMenu(opts)

    def update(self, dt):
        super().update(dt)
        chosen = self.menu.update(self.g, dt)
        if chosen is not None:
            self.g.set_profile(chosen)
            self.g.switch_mode(MainMenu(self.g))

    def draw(self, s):
        g = self.g
        s.blit(g.txt_title_big, ((g.W - g.txt_title_big.get_width()) / 2, g.H * 0.09))
        sub = g.txt_who
        s.blit(sub, ((g.W - sub.get_width()) / 2, g.H * 0.26))
        self.menu.draw(s, g)
        for opt in self.menu.options:  # sterren + trofeeën van elk profiel eronder
            ox, oy = opt["pos"]
            s.blit(opt["sub"], (ox - opt["sub"].get_width() / 2, oy + opt["r"] + 70))
        if not g.cursors:
            g.draw_invite(s, text_y=0.90, with_icon=False)
        super().draw(s)


class MainMenu(Mode):
    label = "Hoofdmenu"
    show_score = False

    def __init__(self, game):
        super().__init__(game)
        g = game
        defs = [
            ("avontuur", theme.AMBER, g.menu_star_icon, "Avontuur"),
            ("vrij", theme.TEAL, g.freeplay_bubble_icon, "Vrij spelen"),
            ("trofee", theme.LILA, g.trophy_icon, "Trofeeën"),
        ]
        self.menu = HoverMenu([
            {"pos": (g.W * (0.25 + 0.25 * i), g.H * 0.55), "r": 120,
             "sprite": g.menu_bubbles_big[color], "icon": icon, "payload": key,
             "label": theme.font(38, bold=True).render(label, True, (255, 255, 255))}
            for i, (key, color, icon, label) in enumerate(defs)
        ])

    def update(self, dt):
        super().update(dt)
        g = self.g
        chosen = self.menu.update(g, dt)
        if chosen == "avontuur":
            g.switch_mode(AdventureMenu(g))
        elif chosen == "vrij":
            g.switch_mode(FreePlayMenu(g))
        elif chosen == "trofee":
            g.switch_mode(TrophyRoom(g))

    def draw(self, s):
        g = self.g
        s.blit(g.txt_title_big, ((g.W - g.txt_title_big.get_width()) / 2, g.H * 0.09))
        name, color = profiles.STARS[g.profile_idx]
        p = g.profile
        sub = theme.font(38).render(
            f"{name}  ·  {p['total_stars']} sterren", True, color)
        s.blit(sub, ((g.W - sub.get_width()) / 2, g.H * 0.26))
        self.menu.draw(s, g)
        if not g.cursors:
            g.draw_invite(s, text_y=0.90, with_icon=False)
        super().draw(s)


class FreePlayMenu(Mode):
    label = "Vrij spelen"
    show_score = False

    def __init__(self, game):
        super().__init__(game)
        g = game
        opts = []
        for i, (cls, color, icon_attr, label) in enumerate(FREE_GAMES):
            row, col = divmod(i, 5)
            opts.append({
                "pos": (g.W * (0.10 + 0.20 * col), g.H * (0.38 + 0.32 * row)), "r": 88,
                "sprite": g.menu_bubbles_small[color], "icon": getattr(g, icon_attr),
                "payload": cls,
                "label": theme.font(27, bold=True).render(label, True, (255, 255, 255)),
            })
        self.menu = HoverMenu(opts)

    def update(self, dt):
        super().update(dt)
        chosen = self.menu.update(self.g, dt)
        if chosen is not None:
            self.g.start_game(chosen)

    def draw(self, s):
        g = self.g
        sub = g.txt_choose
        s.blit(sub, ((g.W - sub.get_width()) / 2, g.H * 0.13))
        self.menu.draw(s, g)
        if not g.cursors:
            g.draw_invite(s, text_y=0.92, with_icon=False)
        super().draw(s)


class AdventureMenu(Mode):
    label = "Avontuur"
    show_score = False

    def __init__(self, game):
        super().__init__(game)
        g = game
        done = g.profile["adv_done"]
        opts = []
        for i, (name, color, stages) in enumerate(ADVENTURES):
            x = g.W * (0.10 + 0.20 * i)
            y = g.H * (0.50 + (0.10 if i % 2 else -0.02))
            if i < done:      # klaar: trofee in de bel, opnieuw spelen mag
                icon, badge = g.trophy_minis[i], None
            elif i == done:   # huidige: ster, pulserende ring in draw()
                icon, badge = g.menu_star_icon, None
            else:             # nog op slot
                icon, badge = None, g.lock_sprite
            opts.append({"pos": (x, y), "r": 96, "sprite": g.menu_bubbles_adv[color],
                         "icon": icon, "badge": badge, "payload": i,
                         "enabled": i <= done,
                         "label": theme.font(30, bold=True).render(name, True, (255, 255, 255))})
        self.menu = HoverMenu(opts)
        self.done = done

    def update(self, dt):
        super().update(dt)
        chosen = self.menu.update(self.g, dt)
        if chosen is not None:
            self.g.start_adventure(chosen)

    def draw(self, s):
        g = self.g
        title = g.txt_adventure
        s.blit(title, ((g.W - title.get_width()) / 2, g.H * 0.10))
        # pad tussen de avonturen
        pts = [opt["pos"] for opt in self.menu.options]
        pygame.draw.lines(s, (86, 90, 132), False, [(x, y) for x, y in pts], 4)
        self.menu.draw(s, g)
        if self.done < len(ADVENTURES):
            # pulserende ring om het huidige avontuur + etappestipjes
            opt = self.menu.options[self.done]
            ox, oy = opt["pos"]
            rr = int(opt["r"] + 16 + math.sin(self.t * 3.5) * 6)
            pygame.draw.circle(s, theme.AMBER, (int(ox), int(oy)), rr, 4)
            stages = ADVENTURES[self.done][2]
            stage = g.profile["adv_stage"]
            for j in range(len(stages)):
                col = theme.AMBER if j < stage else (95, 99, 138)
                pygame.draw.circle(s, col, (int(ox - len(stages) * 12 + 12 + j * 24),
                                            int(oy - opt["r"] - 26)), 8)
        else:
            txt = g.txt_all_done
            s.blit(txt, ((g.W - txt.get_width()) / 2, g.H * 0.80))
        if not g.cursors:
            g.draw_invite(s, text_y=0.90, with_icon=False)
        super().draw(s)


class TrophyRoom(Mode):
    label = "Trofeeën"
    show_score = False

    def __init__(self, game):
        super().__init__(game)

    def update(self, dt):
        super().update(dt)

    def draw(self, s):
        g = self.g
        title = g.txt_trophies
        s.blit(title, ((g.W - title.get_width()) / 2, g.H * 0.10))
        done = g.profile["adv_done"]
        shelf_y = g.H * 0.58
        pygame.draw.line(s, (120, 96, 70), (g.W * 0.06, shelf_y + 8),
                         (g.W * 0.94, shelf_y + 8), 10)
        for i, (name, color, _) in enumerate(ADVENTURES):
            x = g.W * (0.14 + 0.18 * i)
            spr = g.trophy_sprites[i] if i < done else g.trophy_shadow
            bob = math.sin(time.time() * 1.8 + i) * 4 if i < done else 0
            s.blit(spr, (x - spr.get_width() / 2, shelf_y - spr.get_height() + 6 + bob))
            col = color if i < done else (120, 124, 160)
            txt = theme.font(28, bold=True).render(name, True, col)
            s.blit(txt, (x - txt.get_width() / 2, shelf_y + 26))
        p = g.profile
        total = theme.font(48, bold=True).render(
            f"{p['total_stars']} sterren verdiend", True, theme.AMBER)
        star = g.star_hud
        tw = total.get_width() + star.get_width() + 16
        s.blit(star, ((g.W - tw) / 2, g.H * 0.78))
        s.blit(total, ((g.W - tw) / 2 + star.get_width() + 16, g.H * 0.78 - 8))
        super().draw(s)


class TrophyAward(Mode):
    """Feestje na een voltooid avontuur: de trofee zoomt binnen onder confetti."""

    label = "Trofee!"
    show_score = False

    def __init__(self, game, adv_i):
        super().__init__(game)
        self.adv_i = adv_i
        name = ADVENTURES[adv_i][0]
        self.txt = theme.font(64, bold=True).render(
            f"Je hebt de {name}-trofee verdiend!", True, ADVENTURES[adv_i][1])
        game.sounds.fanfare.play()
        self.confetti_timer = 0.0

    def update(self, dt):
        super().update(dt)
        g = self.g
        self.confetti_timer -= dt
        if self.t < 3.5 and self.confetti_timer <= 0:  # confettiregen
            for _ in range(4):
                c = random.choice(theme.PLAY_COLORS)
                g.particles.append(Particle(
                    random.uniform(0, g.W), -20, random.uniform(-60, 60),
                    random.uniform(60, 160), random.uniform(1.2, 2.0),
                    g.confetti[c], gravity=240, additive=False))
            self.confetti_timer = 0.12
        if self.t > 6.0:
            g.switch_mode(AdventureMenu(g))

    def draw(self, s):
        g = self.g
        spr = g.trophy_big[self.adv_i]
        k = min(1.0, self.t / 0.6)
        k = 1 - (1 - k) ** 3  # uitveren
        img = pygame.transform.rotozoom(spr, math.sin(self.t * 2.2) * 5, 0.3 + 0.7 * k)
        s.blit(img, ((g.W - img.get_width()) / 2, g.H * 0.40 - img.get_height() / 2))
        self.txt.set_alpha(int(255 * k))
        s.blit(self.txt, ((g.W - self.txt.get_width()) / 2, g.H * 0.68))
        self.txt.set_alpha(255)
        super().draw(s)
