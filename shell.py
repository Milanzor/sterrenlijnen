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
from modes_body import (BounceMode, BridgeMode, CrystalMode, DanceMode,
                        DragonMode, OrbsMode, RunMode, SmashMode)
from modes_hand import (AnimalsMode, BubblesMode, CatchMode, TraceMode,
                        WhackMode)

# Avonturen: naam, kleur, etappes (spel + sterrendoel). Elk avontuur klaar = trofee.
ADVENTURES = [
    ("Sterrenweide", theme.AMBER, [(BubblesMode, 8), (CatchMode, 8)]),
    ("Bloemenvallei", theme.LIME, [(AnimalsMode, 8), (DragonMode, 8)]),
    ("Kristalgrot", theme.LILA, [(CrystalMode, 8), (TraceMode, 6)]),
    ("Wolkenland", theme.SKY, [(BounceMode, 8), (WhackMode, 8)]),
    ("Feestplaneet", theme.ROSE, [(DanceMode, 8), (OrbsMode, 8)]),
    ("Rotsberg", theme.TEAL, [(SmashMode, 8), (BridgeMode, 6), (RunMode, 8)]),
]

# Vrij spelen: alle dertien spellen. (klasse, belkleur, icoon-attribuut op Game)
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
    (SmashMode, theme.LIME, "smash_icon", "Stenen kraken"),
    (BridgeMode, theme.ROSE, "bridge_icon", "Bruggetje"),
    (RunMode, theme.TEAL, "run_icon", "Ren en spring!"),
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


class TitleMode(Mode):
    """Startscherm: het logo met leven eromheen — zwaaien om te beginnen."""

    label = "Welkom!"
    show_score = False
    show_hud = False
    music = "title"

    def __init__(self, game):
        super().__init__(game)
        g = game
        self.wave_t = 0.0
        self.bubbles = []  # (x, y, snelheid, sprite) — opstijgende sfeerbellen
        for _ in range(7):
            color = random.choice(theme.PLAY_COLORS)
            self.bubbles.append([random.uniform(60, g.W - 60), random.uniform(0, g.H),
                                 random.uniform(30, 70), g.menu_bubbles_small[color]])
        self.dragon_x = -300.0

    def update(self, dt):
        super().update(dt)
        g = self.g
        for b in self.bubbles:
            b[1] -= b[2] * dt
            if b[1] < -110:
                b[0], b[1] = random.uniform(60, g.W - 60), g.H + 110
        self.dragon_x += dt * 150
        if self.dragon_x > g.W + 400:
            self.dragon_x = -400.0
        # even zwaaien (hand in beeld houden) = beginnen
        self.wave_t = self.wave_t + dt if g.cursors else max(0.0, self.wave_t - dt * 2)
        if self.wave_t > 0.8:
            g.sounds.golden.play()
            if g.intro_seen:
                g.switch_mode(ProfileMenu(g))
            else:
                g.switch_mode(IntroMode(g))

    def draw(self, s):
        g = self.g
        for x, y, _v, spr in self.bubbles:
            spr.set_alpha(70)
            s.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2))
            spr.set_alpha(255)
        frame = g.dragon_frames[int(self.t * 9) % len(g.dragon_frames)]
        s.blit(frame, (self.dragon_x, g.H * 0.20 + math.sin(self.t * 2.2) * 30))
        # alien gluurt onderin mee
        peek = math.sin(self.t * 0.9)
        if peek > 0:
            a = g.alien_peek
            s.blit(a, (g.W * 0.82 - a.get_width() / 2,
                       g.H - a.get_height() * 0.55 * min(1.0, peek * 2.2)))
        # logo met gloed en draaiende sterretjes eromheen
        glow = g.title_glow
        s.blit(glow, ((g.W - glow.get_width()) / 2, g.H * 0.30 - glow.get_height() / 2),
               special_flags=pygame.BLEND_ADD)
        title = g.txt_title_big
        s.blit(title, ((g.W - title.get_width()) / 2, g.H * 0.30 - title.get_height() / 2))
        for i in range(5):
            ang = self.t * 0.9 + i * math.tau / 5
            x = g.W / 2 + math.cos(ang) * (title.get_width() / 2 + 90)
            y = g.H * 0.30 + math.sin(ang) * 90
            star = pygame.transform.rotozoom(g.star_fly, -self.t * 80 + i * 40,
                                             0.8 + 0.3 * math.sin(self.t * 3 + i))
            s.blit(star, (x - star.get_width() / 2, y - star.get_height() / 2))
        sub = g.txt_press_start
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.6)
        sub.set_alpha(int(150 + 105 * pulse))
        s.blit(sub, ((g.W - sub.get_width()) / 2, g.H * 0.66))
        sub.set_alpha(255)
        if self.wave_t > 0:  # vulring: zwaaien is 'even volhouden'
            k = min(1.0, self.wave_t / 0.8)
            rect = pygame.Rect(0, 0, 120, 120)
            rect.center = (g.W / 2, g.H * 0.82)
            pygame.draw.arc(s, theme.AMBER, rect, math.pi / 2 - k * math.tau, math.pi / 2, 9)
        super().draw(s)


class IntroMode(Mode):
    """Kort intro'tje in drie plaatjes; overslaan kan met de bel rechtsonder."""

    label = "Intro"
    show_score = False
    show_hud = False
    music = "title"
    SCENE_T = 4.6

    def __init__(self, game):
        super().__init__(game)
        g = game
        self.texts = [
            theme.font(54, bold=True).render(
                "Er kwam een alien uit de sterrenlucht...", True, (255, 255, 255)),
            theme.font(54, bold=True).render(
                "Oeps! Alle sterren vielen eruit!", True, theme.AMBER),
            theme.font(54, bold=True).render(
                "Help jij ze terugvinden? Doe mee met je hele lijf!", True, (255, 255, 255)),
        ]
        self.scene_prev = 0
        rng = random.Random(11)
        self.scatter = [(rng.uniform(0, math.tau), rng.uniform(120, 420),
                         rng.uniform(0.7, 1.4)) for _ in range(12)]
        self.skip = HoverMenu([{
            "pos": (g.W * 0.90, g.H * 0.87), "r": 64,
            "sprite": g.menu_bubbles_small[theme.SKY], "icon": None, "payload": "skip",
            "label": theme.font(26, bold=True).render("Overslaan", True, (255, 255, 255)),
        }])
        self.skip.HOLD = 0.8

    @property
    def scene(self):
        return min(2, int(self.t / self.SCENE_T))

    def _finish(self):
        g = self.g
        g.intro_seen = True
        g.switch_mode(ProfileMenu(g))

    def update(self, dt):
        super().update(dt)
        g = self.g
        if self.scene != self.scene_prev:
            self.scene_prev = self.scene
            (g.sounds.bloop if self.scene == 1 else g.sounds.peep).play()
        if self.skip.update(g, dt) is not None or self.t > 3 * self.SCENE_T:
            self._finish()

    def draw(self, s):
        g = self.g
        scene = self.scene
        local = self.t - scene * self.SCENE_T
        txt = self.texts[scene]
        txt.set_alpha(int(255 * min(1.0, local / 0.5)))
        s.blit(txt, ((g.W - txt.get_width()) / 2, g.H * 0.16))
        txt.set_alpha(255)
        cx, cy = g.W / 2, g.H * 0.52
        if scene == 0:
            # de bel met de alien zweeft naar binnen
            y = cy - 320 * (1 - min(1.0, local / 2.6)) ** 2
            wob = math.sin(self.t * 2.2) * 14
            bub = g.intro_bubble
            s.blit(bub, (cx - bub.get_width() / 2 + wob, y - bub.get_height() / 2))
            alien = g.alien_big
            s.blit(alien, (cx - alien.get_width() / 2 + wob, y - alien.get_height() / 2))
        elif scene == 1:
            # de bel knalt: sterren stuiven alle kanten op
            k = min(1.0, local / 1.6)
            for ang, dist, size in self.scatter:
                x = cx + math.cos(ang) * dist * k
                y = cy + math.sin(ang) * dist * k * 0.7 + 120 * k * k
                star = pygame.transform.rotozoom(g.star_fly, ang * 57 + self.t * 90, size)
                s.blit(star, (x - star.get_width() / 2, y - star.get_height() / 2))
            if local < 0.4:
                pygame.draw.circle(s, theme.AMBER, (int(cx), int(cy)),
                                   int(40 + local * 500), 6)
        else:
            # de alien zwaait, de draak vliegt voorbij: doe mee!
            alien = pygame.transform.rotozoom(g.alien_big, math.sin(self.t * 6) * 10, 1.3)
            s.blit(alien, (cx - alien.get_width() / 2, cy - alien.get_height() / 2))
            frame = g.dragon_frames[int(self.t * 9) % len(g.dragon_frames)]
            dx = -300 + (g.W + 600) * min(1.0, local / self.SCENE_T)
            s.blit(frame, (dx, g.H * 0.30 + math.sin(self.t * 3) * 24))
            hand = g.hand_icon
            s.blit(hand, (g.W * 0.24 - hand.get_width() / 2, cy - hand.get_height() / 2))
            arms = g.cmd_icons["armen"]
            s.blit(arms, (g.W * 0.76 - arms.get_width() / 2, cy - arms.get_height() / 2))
        self.skip.draw(s, g)
        if not g.cursors:
            g.draw_invite(s, text_y=0.92, with_icon=False)
        super().draw(s)


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
            ("opties", theme.SKY, g.gear_icon, "Opties"),
        ]
        self.menu = HoverMenu([
            {"pos": (g.W * (0.16 + 0.68 * i / 3), g.H * 0.55), "r": 112,
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
        elif chosen == "opties":
            g.switch_mode(OptionsMenu(g))

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
            in_row = min(5, len(FREE_GAMES) - row * 5)
            x0 = 0.50 - 0.20 * (in_row - 1) / 2
            opts.append({
                "pos": (g.W * (x0 + 0.20 * col), g.H * (0.30 + 0.235 * row)), "r": 78,
                "sprite": g.menu_bubbles_small[color], "icon": getattr(g, icon_attr),
                "payload": cls,
                "label": theme.font(24, bold=True).render(label, True, (255, 255, 255)),
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
        s.blit(sub, ((g.W - sub.get_width()) / 2, g.H * 0.09))
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
            x = g.W * (0.085 + 0.166 * i)
            y = g.H * (0.50 + (0.10 if i % 2 else -0.02))
            if i < done:      # klaar: trofee in de bel, opnieuw spelen mag
                icon, badge = g.trophy_minis[i], None
            elif i == done:   # huidige: ster, pulserende ring in draw()
                icon, badge = g.menu_star_icon, None
            else:             # nog op slot
                icon, badge = None, g.lock_sprite
            opts.append({"pos": (x, y), "r": 88, "sprite": g.menu_bubbles_adv[color],
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
            x = g.W * (0.11 + 0.156 * i)
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


class OptionsMenu(Mode):
    """Opties: muziek en geluid, de intro terugkijken, of opnieuw beginnen."""

    label = "Opties"
    show_score = False
    COOLDOWN = -1.4  # na een keuze even wachten, anders schakel je in één beweging door

    def __init__(self, game):
        super().__init__(game)
        g = game
        defs = [
            ("muziek", theme.TEAL, None),
            ("geluid", theme.LILA, None),
            ("intro", theme.SKY, g.alien_inner),
            ("reset", theme.CORAL, None),
        ]
        self.menu = HoverMenu([
            {"pos": (g.W * (0.16 + 0.68 * i / 3), g.H * 0.52), "r": 108,
             "sprite": g.menu_bubbles_big[color], "icon": icon, "payload": key,
             "label": None}
            for i, (key, color, icon, ) in enumerate(defs)
        ])
        self._refresh_labels()

    def _refresh_labels(self):
        st = self.g.profiles_data["settings"]
        names = {
            "muziek": f"Muziek: {'aan' if st['music'] else 'uit'}",
            "geluid": f"Geluid: {profiles.VOLUMES[st['volume']][0]}",
            "intro": "Intro bekijken",
            "reset": "Opnieuw beginnen",
        }
        for opt in self.menu.options:
            opt["label"] = theme.font(32, bold=True).render(
                names[opt["payload"]], True, (255, 255, 255))

    def update(self, dt):
        super().update(dt)
        g = self.g
        chosen = self.menu.update(g, dt)
        if chosen is None:
            return
        st = g.profiles_data["settings"]
        if chosen == "muziek":
            st["music"] = not st["music"]
        elif chosen == "geluid":
            st["volume"] = (st["volume"] + 1) % len(profiles.VOLUMES)
        elif chosen == "intro":
            g.switch_mode(IntroMode(g))
            return
        else:
            g.switch_mode(ConfirmReset(g))
            return
        g.apply_settings()
        self._refresh_labels()
        for opt in self.menu.options:  # anti-doorschakel: ring moet opnieuw vullen
            if opt["payload"] == chosen:
                opt["hold"] = self.COOLDOWN

    def draw(self, s):
        g = self.g
        title = g.txt_options
        s.blit(title, ((g.W - title.get_width()) / 2, g.H * 0.10))
        self.menu.draw(s, g)
        if not g.cursors:
            g.draw_invite(s, text_y=0.90, with_icon=False)
        super().draw(s)


class ConfirmReset(Mode):
    """Weet je het zeker? Wist sterren, avonturen en trofeeën van dit profiel."""

    label = "Opnieuw beginnen"
    show_score = False

    def __init__(self, game):
        super().__init__(game)
        g = game
        name, color = profiles.STARS[g.profile_idx]
        self.question = theme.font(48, bold=True).render(
            f"Alles van {name} wissen?", True, color)
        self.menu = HoverMenu([
            {"pos": (g.W * 0.35, g.H * 0.58), "r": 110,
             "sprite": g.menu_bubbles_big[theme.LIME], "icon": None, "payload": "nee",
             "label": theme.font(40, bold=True).render("Nee, bewaren", True, (255, 255, 255))},
            {"pos": (g.W * 0.65, g.H * 0.58), "r": 110,
             "sprite": g.menu_bubbles_big[theme.CORAL], "icon": None, "payload": "ja",
             "label": theme.font(40, bold=True).render("Ja, wissen", True, (255, 255, 255))},
        ])
        self.menu.HOLD = 1.6  # wissen mag niet per ongeluk gaan

    def update(self, dt):
        super().update(dt)
        g = self.g
        chosen = self.menu.update(g, dt)
        if chosen == "ja":
            g.profile.update(total_stars=0, adv_done=0, adv_stage=0)
            profiles.save(g.profiles_data)
            g.sounds.fizzle.play()
            g.switch_mode(OptionsMenu(g))
        elif chosen == "nee":
            g.switch_mode(OptionsMenu(g))

    def draw(self, s):
        g = self.g
        s.blit(self.question, ((g.W - self.question.get_width()) / 2, g.H * 0.24))
        p = g.profile
        sub = theme.font(32).render(
            f"({p['total_stars']} sterren en {p['adv_done']} trofeeën)", True, (215, 219, 248))
        s.blit(sub, ((g.W - sub.get_width()) / 2, g.H * 0.34))
        self.menu.draw(s, g)
        if not g.cursors:
            g.draw_invite(s, text_y=0.90, with_icon=False)
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
