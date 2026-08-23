"""Lijfsignalen uit MediaPipe-pose: klapwieken, klappen, springen, bukken.

De inference-thread voert ~30x per seconde ruwe pose-landmarks aan; hier worden
dat kindvriendelijke signalen. Alles is genormaliseerd op de eigen lichaamsmaat
(schouderbreedte/romplengte), zodat het niet uitmaakt hoe ver het kind van de
camera staat. De hoofdthread leest een snapshot en een events-lijstje.

Klapwieken is bewust continu (energie uit neerwaartse polssnelheid) in plaats
van losse flap-events: dat voelt direct en kan niet "missen" — belangrijk voor
kleuters.
"""
import math
import threading
import time
from dataclasses import dataclass, field

# MediaPipe PoseLandmarker-indexen
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24

FLAP_SPEED_REF = 1.6   # neerwaartse polssnelheid (schermhoogtes/s) voor volle lift
FLAP_DECAY = 0.40      # seconden waarin de flap-energie wegebt
CLAP_CLOSE = 0.60      # handen samen: polsafstand < dit × schouderbreedte
CLAP_OPEN = 1.15       # opnieuw laden zodra de handen weer zo ver uit elkaar zijn
CLAP_COOLDOWN = 0.45
JUMP_RISE = 0.055      # heup zoveel boven de rustlijn (genormaliseerd) = sprong
BASELINE_TAU = 4.0     # rustlijn-heuphoogte volgt langzaam mee
CROUCH_START = 0.045   # heup zoveel onder de rustlijn = begin van bukken
CROUCH_FULL = 0.13
CROSS_NEAR = 0.95      # pols bij de ándere schouder: afstand < dit × schouderbreedte
CROSS_HOLD = 1.1       # zo lang armen gekruist houden = stoppen (LeapMove-gebaar)


@dataclass
class Body:
    """Snapshot voor de hoofdthread; posities genormaliseerd (0..1, y omlaag)."""
    x: float = 0.5             # midden van de schouders
    head: tuple = (0.5, 0.3)
    wrists: list = field(default_factory=list)
    shoulder_w: float = 0.2
    lift: float = 0.0          # 0..1 klapwiek-energie
    arms_up: bool = False
    crouch: float = 0.0        # 0..1
    exit_k: float = 0.0        # 0..1 hoe lang de armen al gekruist zijn (stop-gebaar)
    t: float = 0.0             # wanneer voor het laatst gezien

    @property
    def seen(self) -> bool:
        return time.time() - self.t < 0.6


class BodyTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._body = Body()
        self._events: list[str] = []
        self._prev_wrists: dict[int, tuple[float, float]] = {}
        self._prev_t: float | None = None
        self._flap_energy = 0.0
        self._clap_armed = True
        self._clap_at = 0.0
        self._hip_base: float | None = None
        self._airborne = False
        self._cross_t = 0.0
        self._cross_fired = False

    def feed(self, lm) -> None:
        """Eén pose (lijst van 33 landmarks) uit de inference-thread."""
        now = time.time()
        dt = min(0.2, now - self._prev_t) if self._prev_t else 1 / 30
        self._prev_t = now

        sx = (lm[L_SHOULDER].x + lm[R_SHOULDER].x) / 2
        sy = (lm[L_SHOULDER].y + lm[R_SHOULDER].y) / 2
        hip_y = (lm[L_HIP].y + lm[R_HIP].y) / 2
        shoulder_w = max(0.06, abs(lm[L_SHOULDER].x - lm[R_SHOULDER].x))

        wrists = []
        down_speed = 0.0
        for idx in (L_WRIST, R_WRIST):
            w = lm[idx]
            if getattr(w, "visibility", 1.0) < 0.35:
                self._prev_wrists.pop(idx, None)
                continue
            wrists.append((w.x, w.y))
            prev = self._prev_wrists.get(idx)
            if prev is not None and dt > 0:
                down_speed += max(0.0, (w.y - prev[1]) / dt)
            self._prev_wrists[idx] = (w.x, w.y)

        # klapwiek-energie: snelle attack, rustig verval
        self._flap_energy *= math.exp(-dt / FLAP_DECAY)
        self._flap_energy = max(self._flap_energy,
                                min(1.0, down_speed / (2 * FLAP_SPEED_REF)))
        arms_up = len(wrists) == 2 and all(wy < sy for _, wy in wrists)

        events = []
        events += self._detect_clap(wrists, shoulder_w, now)
        events += self._track_hips(hip_y, dt)
        events += self._detect_cross(lm, shoulder_w, dt)
        crouch = 0.0
        if self._hip_base is not None:
            crouch = min(1.0, max(0.0, (hip_y - self._hip_base - CROUCH_START)
                                  / (CROUCH_FULL - CROUCH_START)))

        with self._lock:
            self._body = Body(x=sx, head=(lm[NOSE].x, lm[NOSE].y), wrists=wrists,
                              shoulder_w=shoulder_w, lift=self._flap_energy,
                              arms_up=arms_up, crouch=crouch,
                              exit_k=min(1.0, self._cross_t / CROSS_HOLD), t=now)
            self._events += events

    def _detect_clap(self, wrists, shoulder_w, now) -> list[str]:
        if len(wrists) < 2:
            return []
        d = math.hypot(wrists[0][0] - wrists[1][0], wrists[0][1] - wrists[1][1])
        if self._clap_armed and d < CLAP_CLOSE * shoulder_w and now - self._clap_at > CLAP_COOLDOWN:
            self._clap_armed = False
            self._clap_at = now
            return ["clap"]
        if not self._clap_armed and d > CLAP_OPEN * shoulder_w:
            self._clap_armed = True
        return []

    def _detect_cross(self, lm, shoulder_w, dt) -> list[str]:
        """Armen gekruist op de schouders (even vasthouden) = stoppen, zoals LeapMove."""
        lw, rw = lm[L_WRIST], lm[R_WRIST]
        if getattr(lw, "visibility", 1.0) < 0.35 or getattr(rw, "visibility", 1.0) < 0.35:
            crossed = False
        else:
            d_l = math.hypot(lw.x - lm[R_SHOULDER].x, lw.y - lm[R_SHOULDER].y)
            d_r = math.hypot(rw.x - lm[L_SHOULDER].x, rw.y - lm[L_SHOULDER].y)
            crossed = d_l < CROSS_NEAR * shoulder_w and d_r < CROSS_NEAR * shoulder_w
        if not crossed:
            self._cross_t = 0.0
            self._cross_fired = False
            return []
        self._cross_t += dt
        if self._cross_t >= CROSS_HOLD and not self._cross_fired:
            self._cross_fired = True
            return ["exit"]
        return []

    def _track_hips(self, hip_y, dt) -> list[str]:
        if self._hip_base is None:
            self._hip_base = hip_y
            return []
        dev = hip_y - self._hip_base
        # rustlijn alleen bijwerken als het kind niet net springt of bukt,
        # anders schuift de lijn mee en verdwijnt het signaal
        if abs(dev) < 0.035:
            self._hip_base += (hip_y - self._hip_base) * min(1.0, dt / BASELINE_TAU)
        if not self._airborne and dev < -JUMP_RISE:
            self._airborne = True
            return ["jump"]
        if self._airborne and dev > -0.02:
            self._airborne = False
        return []

    # ---------- hoofdthread ----------

    def get(self) -> Body:
        with self._lock:
            return self._body

    def poll_events(self) -> list[str]:
        with self._lock:
            ev, self._events = self._events, []
            return ev
