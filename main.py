"""Sterrenbellen — vijf handspellen, vijf lijfspellen en een LeapMove-achtige schil.

Camera-spel voor kinderen. Bij het starten kies je een ster (profiel), daarna:
- Avontuur: vijf avonturen van elk een paar etappes; elk avontuur klaar = trofee.
- Vrij spelen: alle tien spellen los te kiezen.
- Trofeeën: de prijzenkast van dit profiel.

Handspellen (MediaPipe HandLandmarker): bellen prikken, sterren vangen, naar
mama!, aliens tikken, lijnen volgen. Lijfspellen (MediaPipe PoseLandmarker):
vliegende draak, toverballen, kristalgrot, bellen hooghouden, dans!.

Besturing: hand op een keuzebel houden. ESC gaat één stap terug (en stopt
uiteindelijk); Q stopt altijd; F3 toont fps-statistieken. In lijfspellen kun
je ook stoppen door je armen gekruist op je schouders te leggen.
"""
import math
import os
import random
import sys
import time

import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "wayland,x11")

import audio
import profiles
import shell
import theme
from base import (BUBBLE_RADII, DARTER_R, FALL_RADII, GIANT_R, GOLDEN_R,
                  COMET_R, MINI_RADII, PASSENGER_R, HandCursor, Mode)
from camera import CAM_H, CAM_W, CameraTracker
from entities import Particle, PopRing
from modes_body import (BounceMode, BridgeMode, CrystalMode, DanceMode,
                        DragonMode, OrbsMode, RunMode, SmashMode)
from modes_hand import (AnimalsMode, BubblesMode, CatchMode, TraceMode,
                        WhackMode)


class Game:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.mixer.set_reserved(1)
        pygame.mouse.set_visible(False)

        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN, vsync=1)
        except pygame.error:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Sterrenbellen")
        self.W, self.H = self.screen.get_size()

        # camera vult het scherm (cover-fit: schalen tot het past, randen croppen)
        self.cam_scale = max(self.W / CAM_W, self.H / CAM_H)
        self.cam_ox = (self.W - CAM_W * self.cam_scale) / 2
        self.cam_oy = (self.H - CAM_H * self.cam_scale) / 2
        self.cover_size = (round(CAM_W * self.cam_scale), round(CAM_H * self.cam_scale))

        # profielen + instellingen eerst, zodat het volume meteen goed staat
        self.profiles_data = profiles.load()
        self.profile_idx = self.profiles_data["last"]
        self.sounds = audio.Sounds()
        self.apply_settings(save=False)
        self._build_sprites()

        self.cam = CameraTracker(os.path.join(theme.ASSETS, "hand_landmarker.task"),
                                 os.path.join(theme.ASSETS, "pose_landmarker_lite.task"))
        self.bg = pygame.Surface((self.W, self.H)).convert()
        self.bg.fill(theme.VOID_DEEP)
        self.bg_frame_id = -1

        self.cursors: list[HandCursor] = []
        self.particles: list[Particle] = []
        self.rings: list[PopRing] = []
        self.flying: list[FlyingStar] = []
        self.aliens: list = []

        # avontuur-status
        self.adventure: dict | None = None  # {"i": avontuur, "stage": etappe}
        self.stage_done_t = 0.0
        self.intro_seen = False  # het intro'tje speelt één keer per opstart

        self.score_bump = 0.0
        self.last_hands_time = 0.0
        self.show_debug = False
        self.clock = pygame.time.Clock()
        self._score_cache = (None, None)
        self._hud_cache = (None, None)

        self.mode: Mode = shell.TitleMode(self)
        self.sounds.play_music(self.mode.music)

    # ---------- sprites & teksten ----------

    def _build_sprites(self):
        self.bubble_sprites = {}
        for color in theme.PLAY_COLORS:
            for r in BUBBLE_RADII + MINI_RADII + [GIANT_R, PASSENGER_R, DARTER_R]:
                self.bubble_sprites[(color, r)] = theme.make_bubble(r, color)
        self.bubble_sprites[(theme.AMBER, GOLDEN_R)] = theme.make_bubble(GOLDEN_R, theme.AMBER)

        self.tip_glow = theme.make_glow(20, (255, 240, 200), peak=190)
        self.palm_glow = theme.make_glow(44, (255, 214, 130), peak=90)
        self.spark = theme.make_glow_levels(9, (255, 250, 230), peak=255, falloff=1.6)
        self.droplets = {c: theme.make_glow_levels(11, c, peak=235, falloff=1.8) for c in theme.PLAY_COLORS}
        self.droplets[theme.AMBER] = theme.make_glow_levels(13, theme.AMBER, peak=235, falloff=1.8)
        self.confetti = {c: theme.make_star(12, c, glow=False) for c in theme.PLAY_COLORS}
        self.star_fly = theme.make_star(20)
        self.star_hud = theme.make_star(24)
        self.star_inner = theme.make_star(int(GOLDEN_R * 0.5))
        self.fall_sprites = {r: theme.make_star(r) for r in FALL_RADII}
        self.comet_sprite = theme.make_star(COMET_R, theme.SKY)
        self.alien_big = theme.make_alien(120)
        self.alien_inner = theme.make_alien(int(PASSENGER_R * 1.15))
        self.hand_icon = theme.make_hand_icon(150)
        self.menu_star_icon = theme.make_star(60)
        self.menu_chick_icon = theme.make_chick(95)
        self.menu_trace_icon = theme.make_trace_icon(105)

        # keuzebellen in drie maten: hoofdmenu, vrij spelen en avontuur
        self.menu_bubbles_big = {c: theme.make_bubble(112, c)
                                 for c in set(theme.PLAY_COLORS) | {theme.AMBER}}
        self.menu_bubbles_small = {c: theme.make_bubble(78, c) for c in theme.PLAY_COLORS}
        self.menu_bubbles_adv = {c: theme.make_bubble(88, c)
                                 for c in set(theme.PLAY_COLORS) | {theme.AMBER}}
        self.freeplay_bubble_icon = self.bubble_sprites[(theme.TEAL, 56)]

        # diertjes: (baby, baby gespiegeld) + mama per soort, in dezelfde volgorde
        self.animal_baby = []
        self.animal_parent = []
        for mk in (theme.make_chick, theme.make_frog, theme.make_bunny):
            baby = mk(84)
            self.animal_baby.append((baby, pygame.transform.flip(baby, True, False)))
            self.animal_parent.append(mk(185))
        self.nest_sprite = theme.make_nest(230)
        self.heart_sprite = theme.make_heart(30)
        self.alien_peek = theme.make_alien(180)

        # Vliegende draak: sprite-animaties (CC0) + procedurele wolkjes en flora
        self.dragon_frames = theme.load_frames("dragon", 185)
        self.bee_frames = theme.load_frames("bee", 82)
        self.menu_dragon_icon = pygame.transform.smoothscale_by(
            self.dragon_frames[1], 150 / self.dragon_frames[1].get_width())
        self.cloud_sprite = theme.make_storm_cloud(215)
        self.pickup_star = theme.make_star(34)
        self.fire_glow = theme.make_glow_levels(44, (255, 158, 64), peak=255, falloff=1.5)
        self.flower_sprites = {c: theme.make_flower(88, c)
                               for c in (theme.CORAL, theme.LILA, theme.ROSE, theme.SKY)}
        self.grass_sprites = [theme.make_grass(sz) for sz in (72, 96)]

        # Toverballen
        orb_colors = [c for _, c in OrbsMode.COLOR_NAMES]
        self.orb_sprites = {c: theme.make_orb(46, c) for c in orb_colors}
        self.orb_sprites_small = {c: theme.make_orb(30, c) for c in orb_colors}
        self.orb_icon = self.orb_sprites_small[theme.CORAL]

        # Kristalgrot
        self.crystal_sprites = [theme.make_crystal(250, 400, c)
                                for c in (theme.LILA, theme.TEAL, theme.SKY)]
        self.crystal_icon = theme.make_crystal(62, 100, theme.LILA)
        self.key_sprite = theme.make_key(96)
        self.beam_sprite = pygame.transform.smoothscale(
            theme.make_glow(220, (255, 240, 190), peak=125), (460, self.H + 120))
        self.warn_glow = pygame.transform.smoothscale(
            theme.make_glow(240, theme.AMBER, peak=150), (int(self.W * 0.85), 340))

        # Bellen hooghouden
        self.bounce_sprites = {c: theme.make_bubble(85, c)
                               for c in (theme.TEAL, theme.CORAL, theme.LILA, theme.LIME)}
        self.count_digits = [theme.font(76, bold=True).render(str(i), True, (255, 255, 255))
                             for i in range(5)]
        self.bounce_icon = theme.make_bubble(52, theme.SKY)
        self.bounce_icon.blit(self.count_digits[3], (
            52 - self.count_digits[3].get_width() / 2, 52 - self.count_digits[3].get_height() / 2))

        # Dans!
        self.cmd_icons = {k: theme.make_cmd_icon(k, 190)
                          for k in ("spring", "klap", "buk", "zwaai", "armen")}
        self.dance_icon = theme.make_cmd_icon("zwaai", 92)

        # Stenen kraken: barst-stadia per kristalkleur en formaat
        self.rock_sprites = {(c, sz): [theme.make_rock(sz, c, st) for st in range(3)]
                             for c in (theme.CORAL, theme.SKY, theme.LILA, theme.LIME)
                             for sz in (175, 230)}
        self.smash_icon = theme.make_rock(88, theme.CORAL, 2)

        # Bruggetje
        self.cliff_sprite = theme.make_cliff(250, int(self.H * 0.46))
        mini = theme.make_cliff(46, 64)
        self.bridge_icon = pygame.Surface((150, 80), pygame.SRCALPHA)
        self.bridge_icon.blit(mini, (0, 12))
        self.bridge_icon.blit(mini, (104, 12))
        pygame.draw.line(self.bridge_icon, (192, 142, 88), (40, 18), (110, 18), 7)

        # Ren en spring! — de kip kijkt van zichzelf naar links, wij rennen naar rechts
        self.chicken_frames = [pygame.transform.flip(f, True, False)
                               for f in theme.load_frames("chicken", 170)]
        self.run_icon = pygame.transform.smoothscale_by(
            self.chicken_frames[0], 92 / self.chicken_frames[0].get_height())
        self.log_sprite = theme.make_log(150, 115)
        self.branch_sprite = theme.make_branch(310, 165)
        self.trap_sprite = theme.make_bubble(120, theme.LILA)

        # schil-iconen
        self.gear_icon = theme.make_gear(105)
        self.intro_bubble = theme.make_bubble(150, theme.LILA)

        # schil: profielen, trofeeën, sloten
        self.profile_star_icons = [theme.make_star(58, color)
                                   for _, color in profiles.STARS]
        self.trophy_sprites = [theme.make_trophy(150, color)
                               for _, color, _ in shell.ADVENTURES]
        self.trophy_big = [theme.make_trophy(320, color)
                           for _, color, _ in shell.ADVENTURES]
        self.trophy_minis = [theme.make_trophy(96, color)
                             for _, color, _ in shell.ADVENTURES]
        self.trophy_shadow = theme.make_trophy(150, (74, 78, 108))
        self.trophy_icon = theme.make_trophy(110, theme.AMBER)
        self.lock_sprite = theme.make_lock(96)

        self.vignette = theme.make_vignette(self.W, self.H)
        self.starfield = theme.make_starfield(self.W, self.H)

        self.txt_title = theme.font(38, bold=True).render("Sterrenbellen", True, theme.AMBER)
        self.txt_title_big = theme.font(110, bold=True).render("Sterrenbellen", True, theme.AMBER)
        self.title_glow = pygame.transform.smoothscale(
            theme.make_glow(220, theme.AMBER, peak=60),
            (self.txt_title_big.get_width() + 260, 300))
        self.txt_press_start = theme.font(52, bold=True).render(
            "Zwaai met je hand om te beginnen!", True, (255, 255, 255))
        self.txt_options = theme.font(72, bold=True).render("Opties", True, theme.AMBER)
        self.txt_shake_free = theme.font(64, bold=True).render(
            "Schud je armen!", True, theme.AMBER)
        self.txt_invite = theme.font(56, bold=True).render("Zwaai met je handen!", True, (255, 255, 255))
        self.txt_invite_body = theme.font(56, bold=True).render(
            "Ga staan en beweeg je armen!", True, (255, 255, 255))
        self.txt_choose = theme.font(40).render("Houd je hand op een bel om te kiezen", True, (220, 224, 255))
        self.txt_who = theme.font(52, bold=True).render("Wie speelt er?", True, (255, 255, 255))
        self.txt_adventure = theme.font(72, bold=True).render("Avontuur", True, theme.AMBER)
        self.txt_trophies = theme.font(72, bold=True).render("Trofeeën", True, theme.AMBER)
        self.txt_all_done = theme.font(44, bold=True).render(
            "Alle trofeeën verdiend! Speel gerust nog een keer.", True, theme.AMBER)
        self.txt_stop = theme.font(30, bold=True).render("stoppen...", True, theme.AMBER)
        self.txt_light_comes = theme.font(56, bold=True).render(
            "Het licht komt! Verstop je!", True, (255, 255, 255))
        self.txt_well_hidden = theme.font(64, bold=True).render("Goed verstopt!", True, theme.AMBER)
        self.txt_almost = theme.font(44, bold=True).render(
            "Bijna! Probeer de volgende maar", True, (235, 238, 255))
        self.txt_stage_done = theme.font(110, bold=True).render("Gehaald!", True, theme.AMBER)

    def _score_text(self):
        goal = self.adventure_goal
        key = (self.mode.stars, goal)
        if self._score_cache[0] != key:
            txt = f"{self.mode.stars}/{goal}" if goal else str(self.mode.stars)
            surf = theme.font(64, bold=True).render(txt, True, (255, 255, 255))
            self._score_cache = (key, surf)
        return self._score_cache[1]

    def _hud_text(self):
        key = (self.mode.label, self.mode.level, self.mode.show_score, bool(self.adventure))
        if self._hud_cache[0] != key:
            if self.adventure and self.mode.show_score:
                name = shell.ADVENTURES[self.adventure["i"]][0]
                txt = f"{name} · {self.mode.label}"
            elif self.mode.show_score:
                txt = f"{self.mode.label} · Level {self.mode.level}"
            else:
                txt = self.mode.label
            self._hud_cache = (key, theme.font(28).render(txt, True, (210, 214, 245)))
        return self._hud_cache[1]

    # ---------- profiel & avontuur ----------

    @property
    def profile(self) -> dict:
        return self.profiles_data["profiles"][self.profile_idx]

    def set_profile(self, idx: int):
        self.profile_idx = idx
        self.profiles_data["last"] = idx
        profiles.save(self.profiles_data)

    def apply_settings(self, save: bool = True):
        st = self.profiles_data["settings"]
        self.sounds.set_master(profiles.VOLUMES[st["volume"]][1])
        self.sounds.set_music(st["music"])
        if save:
            profiles.save(self.profiles_data)

    def _bank_stars(self):
        """Verdiende sterren van de aflopende spelronde bij het profiel optellen."""
        if self.mode.show_score and self.mode.stars > 0:
            self.profile["total_stars"] += self.mode.stars
            profiles.save(self.profiles_data)

    def start_game(self, cls):
        self.adventure = None
        self.switch_mode(cls(self))

    def start_adventure(self, i: int):
        stage = self.profile["adv_stage"] if i == self.profile["adv_done"] else 0
        stage = min(stage, len(shell.ADVENTURES[i][2]) - 1)
        self.adventure = {"i": i, "stage": stage}
        cls, _goal = shell.ADVENTURES[i][2][stage]
        self.switch_mode(cls(self))

    @property
    def adventure_goal(self) -> int | None:
        if not self.adventure or not self.mode.show_score:
            return None
        return shell.ADVENTURES[self.adventure["i"]][2][self.adventure["stage"]][1]

    def _check_adventure(self, dt):
        goal = self.adventure_goal
        if goal is None:
            return
        if self.stage_done_t <= 0 and self.mode.stars >= goal:
            self.stage_done_t = 2.4
            self.sounds.tada.play()
            for _ in range(20):
                c = random.choice(theme.PLAY_COLORS)
                self.particles.append(Particle(
                    self.W / 2, self.H * 0.35, random.uniform(-460, 460),
                    random.uniform(-620, -140), random.uniform(0.8, 1.4),
                    self.confetti[c], gravity=700, additive=False))
        elif self.stage_done_t > 0:
            self.stage_done_t -= dt
            if self.stage_done_t <= 0:
                self._advance_adventure()

    def _advance_adventure(self):
        adv = self.adventure
        i, stage = adv["i"], adv["stage"] + 1
        stages = shell.ADVENTURES[i][2]
        current = i == self.profile["adv_done"]
        if stage < len(stages):
            adv["stage"] = stage
            if current:
                self.profile["adv_stage"] = stage
            self._bank_stars()
            cls, _goal = stages[stage]
            self.switch_mode(cls(self), banked=True)
        else:
            if current:
                self.profile["adv_done"] += 1
                self.profile["adv_stage"] = 0
            self._bank_stars()
            self.adventure = None
            self.switch_mode(shell.TrophyAward(self, i), banked=True)

    def go_back(self) -> bool:
        """ESC of het stop-gebaar: één niveau terug. False = spel afsluiten."""
        m = self.mode
        self.stage_done_t = 0.0
        if isinstance(m, shell.TrophyAward):
            self.switch_mode(shell.AdventureMenu(self))
        elif m.show_score:  # een spel
            in_adventure = self.adventure is not None
            self.adventure = None
            self.switch_mode(shell.AdventureMenu(self) if in_adventure
                             else shell.FreePlayMenu(self))
        elif isinstance(m, (shell.FreePlayMenu, shell.AdventureMenu,
                            shell.TrophyRoom, shell.OptionsMenu)):
            self.switch_mode(shell.MainMenu(self))
        elif isinstance(m, shell.ConfirmReset):
            self.switch_mode(shell.OptionsMenu(self))
        elif isinstance(m, shell.MainMenu):
            self.switch_mode(shell.ProfileMenu(self))
        elif isinstance(m, shell.IntroMode):  # intro overslaan
            self.intro_seen = True
            self.switch_mode(shell.ProfileMenu(self))
        elif isinstance(m, shell.ProfileMenu):
            self.switch_mode(shell.TitleMode(self))
        else:  # titelscherm: stoppen
            return False
        return True

    # ---------- gedeeld ----------

    def to_screen(self, nx, ny):
        return (nx * CAM_W * self.cam_scale + self.cam_ox,
                ny * CAM_H * self.cam_scale + self.cam_oy)

    def switch_mode(self, mode: Mode, banked: bool = False):
        if not banked:
            self._bank_stars()
        self.mode = mode
        self._score_cache = (None, None)
        self.sounds.play_music(mode.music)
        self.cam.set_tracking(mode.needs)
        if mode.needs == "body":
            self.cursors = []
            self.cam.poll_body_events()  # oude events (van vóór deze modus) weggooien

    def spawn_pop_effects(self, x, y, radius, color, small=False):
        self.rings.append(PopRing(x, y, radius, color))
        drop = self.droplets[color if color in self.droplets else theme.AMBER]
        for _ in range(7 if small else 12):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(120, 420)
            self.particles.append(Particle(x, y, math.cos(ang) * sp, math.sin(ang) * sp - 60,
                                           random.uniform(0.35, 0.7), drop))

    @property
    def hud_star_pos(self):
        return (self.W - 150, 58)

    # ---------- handen ----------

    def update_cursors(self, dt):
        hands = self.cam.get_hands()
        if hands:
            self.last_hands_time = time.time()
        targets = []
        for h in hands:
            tips = [self.to_screen(*p) for p in h.tips]
            palm = self.to_screen(*h.palm)
            targets.append((tips, palm, h.openness))

        # koppel detecties aan bestaande cursors op palm-afstand
        unmatched = list(range(len(self.cursors)))
        for tips, palm, openness in targets:
            best, best_d = None, 1e9
            for i in unmatched:
                c = self.cursors[i]
                d = math.hypot(c.palm[0] - palm[0], c.palm[1] - palm[1])
                if d < best_d:
                    best, best_d = i, d
            if best is not None and best_d < 420:
                self.cursors[best].set_target(tips, palm, openness)
                unmatched.remove(best)
            else:
                self.cursors.append(HandCursor(tips, palm))

        now = time.time()
        self.cursors = [c for c in self.cursors if now - c.last_seen < 0.35]
        for c in self.cursors:
            c.update(dt)

    def emit_sparkles(self, dt):
        for c in self.cursors:
            for prev, cur in zip(c.prev_tips, c.tips):
                speed = math.hypot(cur[0] - prev[0], cur[1] - prev[1]) / max(dt, 1e-4)
                if speed > 250 and random.random() < min(0.9, speed / 2500):
                    self.particles.append(Particle(
                        cur[0] + random.uniform(-6, 6), cur[1] + random.uniform(-6, 6),
                        random.uniform(-40, 40), random.uniform(-20, 60),
                        random.uniform(0.25, 0.5), self.spark, gravity=140))

    # ---------- hoofdloop ----------

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(165) / 1000.0, 0.05)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_q:
                        running = False
                    elif ev.key == pygame.K_ESCAPE:
                        if not self.go_back():
                            running = False
                    elif ev.key == pygame.K_F3:
                        self.show_debug = not self.show_debug
            self.update(dt)
            self.draw()
            pygame.display.flip()
        self._bank_stars()
        self.cam.stop()
        pygame.quit()

    def update(self, dt):
        self.update_cursors(dt)
        self.mode.update(dt)
        self._check_adventure(dt)
        self.emit_sparkles(dt)
        self.particles = [p for p in self.particles if p.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]
        done = [f for f in self.flying if not f.update(dt)]
        if done:
            self.score_bump = 0.25
        self.flying = [f for f in self.flying if f not in done]
        self.aliens = [a for a in self.aliens if a.update(dt, self.H)]
        self.score_bump = max(0.0, self.score_bump - dt)

    def _refresh_background(self):
        fid, frame = self.cam.get_frame()
        if frame is None or fid == self.bg_frame_id:
            return
        self.bg_frame_id = fid
        surf = pygame.image.frombuffer(frame.tobytes(), (CAM_W, CAM_H), "RGB")
        scaled = pygame.transform.smoothscale(surf, self.cover_size)
        self.bg.blit(scaled, (self.cam_ox, self.cam_oy))
        self.bg.blit(self.vignette, (0, 0))
        self.bg.blit(self.starfield, (0, 0))

    def draw(self):
        self._refresh_background()
        s = self.screen
        s.blit(self.bg, (0, 0))
        self.mode.draw(s)
        for r in self.rings:
            r.draw(s)
        for p in self.particles:
            p.draw(s)
        for a in self.aliens:
            a.draw(s)
        for f in self.flying:
            f.draw(s)
        self._draw_cursors(s)
        self._draw_hud(s)
        if self.stage_done_t > 0:
            k = min(1.0, (2.4 - self.stage_done_t) / 0.25)
            txt = pygame.transform.rotozoom(self.txt_stage_done, 0, 0.6 + 0.4 * k)
            s.blit(txt, ((self.W - txt.get_width()) / 2, self.H * 0.30 - txt.get_height() / 2))
        if (self.mode.show_score and self.mode.needs == "hands"
                and time.time() - self.last_hands_time > 6):
            self.draw_invite(s)
        if self.show_debug:
            self._draw_debug(s)

    def _draw_cursors(self, s):
        for c in self.cursors:
            s.blit(self.palm_glow, (c.palm[0] - 44, c.palm[1] - 44), special_flags=pygame.BLEND_ADD)
            for tip in c.tips:
                s.blit(self.tip_glow, (tip[0] - 20, tip[1] - 20), special_flags=pygame.BLEND_ADD)
                pygame.draw.circle(s, (255, 255, 255), (int(tip[0]), int(tip[1])), 5)

    def _draw_hud(self, s):
        if not self.mode.show_hud:
            return
        pygame.draw.line(s, (82, 86, 128), (24, 96), (self.W - 24, 96), 1)
        s.blit(self.txt_title, (36, 20))
        s.blit(self._hud_text(), (40, 58))
        if self.mode.show_score:
            k = 1 + self.score_bump * 1.2
            star = self.star_hud if k == 1 else pygame.transform.rotozoom(self.star_hud, 0, k)
            sx, sy = self.hud_star_pos
            s.blit(star, (sx - star.get_width() / 2, sy - star.get_height() / 2))
            score = self._score_text()
            s.blit(score, (sx + 44, sy - score.get_height() / 2))

    def draw_invite(self, s, icon_y=0.40, text_y=0.62, with_icon=True, text=None):
        t = time.time()
        pulse = 0.5 + 0.5 * math.sin(t * 2.4)
        if with_icon:
            wave = math.sin(t * 5) * 16
            icon = pygame.transform.rotozoom(self.hand_icon, wave, 0.9 + pulse * 0.12)
            s.blit(icon, ((self.W - icon.get_width()) / 2, self.H * icon_y))
        inv = text if text is not None else self.txt_invite
        inv.set_alpha(int(170 + 85 * pulse))
        s.blit(inv, ((self.W - inv.get_width()) / 2, self.H * text_y))
        inv.set_alpha(255)

    def _draw_debug(self, s):
        if self.mode.needs == "body":
            b = self.cam.get_body()
            detail = (f"lijf {self.cam.infer_fps:4.1f} Hz | lift {b.lift:.2f} | "
                      f"buk {b.crouch:.2f} | armen {'op' if b.arms_up else 'neer'}")
        else:
            opens = " ".join(f"{c.open_k:.2f}" for c in self.cursors)
            detail = f"handen {self.cam.infer_fps:4.1f} Hz | open [{opens}]"
        msg = (f"render {self.clock.get_fps():5.1f} fps | camera {self.cam.capture_fps:4.1f} | "
               f"{detail} | deeltjes {len(self.particles)}")
        surf = theme.font(22).render(msg, True, (255, 255, 255))
        bgr = pygame.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bgr.fill(theme.VOID_DEEP)
        bgr.set_alpha(190)
        s.blit(bgr, (16, self.H - 46))
        s.blit(surf, (24, self.H - 42))


CLI_MODES = {"bellen": BubblesMode, "vangen": CatchMode, "mama": AnimalsMode,
             "aliens": WhackMode, "lijnen": TraceMode, "draak": DragonMode,
             "toverballen": OrbsMode, "kristal": CrystalMode,
             "hooghouden": BounceMode, "dans": DanceMode, "stenen": SmashMode,
             "brug": BridgeMode, "rennen": RunMode}

if __name__ == "__main__":
    try:
        game = Game()
        # optioneel direct in een spel starten, met het laatst gekozen profiel:
        # `uv run main.py bellen|vangen|mama|aliens|lijnen|draak|toverballen|kristal|hooghouden|dans`
        if len(sys.argv) > 1 and sys.argv[1] in CLI_MODES:
            game.start_game(CLI_MODES[sys.argv[1]])
        game.run()
    except RuntimeError as e:
        print(f"Fout: {e}", file=sys.stderr)
        sys.exit(1)
