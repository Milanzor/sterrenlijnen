"""Procedurele audio: geen bestanden, alles met numpy gesynthetiseerd.

Pops lopen een pentatonische ladder op (zoals Zeepbellen in digigamez): elke
prik is de volgende noot, na anderhalve seconde stilte begint de ladder opnieuw.

Achtergrondmuziek is er ook: elk spel heeft zijn eigen vrolijke deuntje,
gecomponeerd als toonladder-graden (C-majeur) en hier gesynthetiseerd tot een
naadloze loop (melodie + baslijn + zachte percussie). Noot-staarten die over
het loop-einde heen rinkelen worden teruggevouwen naar het begin, zodat de
overgang onhoorbaar is.
"""
import numpy as np
import pygame

SR = 44100

# C-majeur pentatonisch over twee octaven
PENTA = [261.63, 293.66, 329.63, 392.00, 440.00,
         523.25, 587.33, 659.26, 784.00, 880.00]

MAJOR = [0, 2, 4, 5, 7, 9, 11]  # toonladder-graden → halve tonen


def _deg_freq(deg: int, octave: int = 0) -> float:
    """Graad in C-majeur (0 = C4; negatief en >6 mag) naar frequentie."""
    midi = 60 + 12 * (octave + deg // 7) + MAJOR[deg % 7]
    return 440.0 * 2 ** ((midi - 69) / 12)


def _to_sound(mono: np.ndarray, volume: float = 1.0) -> pygame.mixer.Sound:
    mono = np.clip(mono * volume, -1.0, 1.0)
    pcm = (mono * 32000).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _env(n: int, attack: float = 0.004, release: float = 0.9) -> np.ndarray:
    t = np.linspace(0, 1, n)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    r = np.exp(-t / release * 6)
    return a * r


def _tone(freq: float, dur: float, detune: float = 1.003) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    w = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2 * t) \
        + 0.35 * np.sin(2 * np.pi * freq * detune * t)
    return w * _env(n)


# ---------------------------------------------------------------- muziekjes

def _synth_note(freq: float, dur: float, timbre: str) -> np.ndarray:
    """Eén melodienoot mét natuurlijke uitklink-staart (langer dan `dur`)."""
    ring = dur + (0.40 if timbre == "pluck" else 0.25)
    n = int(SR * ring)
    t = np.arange(n) / SR
    if timbre == "pluck":  # klokkenspel-achtig tokkeltje
        w = (np.sin(2 * np.pi * freq * t) + 0.45 * np.sin(2 * np.pi * freq * 2 * t)
             + 0.18 * np.sin(2 * np.pi * freq * 3 * t))
        env = np.clip(t / 0.004, 0, 1) * np.exp(-t / max(0.14, dur * 0.55))
    else:  # "soft": fluitig, zachte inzet
        w = (np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
             + 0.3 * np.sin(2 * np.pi * freq * 1.004 * t))
        env = np.clip(t / 0.05, 0, 1) * np.exp(-np.maximum(0.0, t - dur) * 14) \
            * np.exp(-t * 0.7)
    return w * env


def _kick(n_total: int) -> np.ndarray:
    n = int(SR * 0.10)
    t = np.arange(n) / SR
    f = 130 * np.exp(-t * 24) + 48
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 26)
    return w[:n_total] if n_total < n else w


def _hat(rng) -> np.ndarray:
    n = int(SR * 0.045)
    noise = rng.uniform(-1, 1, n)
    noise -= np.convolve(noise, np.ones(24) / 24, mode="same")  # laag eruit
    return noise * np.exp(-np.arange(n) / SR * 90)


# Melodieën als (tel, duur, graad-index-in-akkoord). De indexen wijzen in
# [grondtoon, terts, kwint, octaaf, none] zodat alles vanzelf consonant blijft.
_CHORD_STEPS = [0, 2, 4, 7, 9]


def _render_tune(bpm: float, chords: list, rhythm_a: list, rhythm_b: list,
                 octave: int, timbre: str, hat: bool, kick: bool,
                 bpb: int = 4, seed: int = 5) -> pygame.mixer.Sound:
    """Bouwt een naadloze muziekloop: melodie + bas (+ tik en boem)."""
    rng = np.random.default_rng(seed)
    spb = 60.0 / bpm
    beats = len(chords) * bpb
    total = int(SR * beats * spb)
    buf = np.zeros(total + SR)  # extra ruimte voor uitklinkende staarten

    def add(sample: np.ndarray, at_beat: float, gain: float) -> None:
        i = int(at_beat * spb * SR)
        seg = sample[: buf.size - i]
        buf[i:i + seg.size] += seg * gain

    for bar, root in enumerate(chords):
        bar_beat = bar * bpb
        rhythm = rhythm_a if bar % 2 == 0 else rhythm_b
        for off, dur, step in rhythm:
            deg = root + _CHORD_STEPS[step % len(_CHORD_STEPS)]
            add(_synth_note(_deg_freq(deg, octave), dur * spb, timbre),
                bar_beat + off, 0.50)
        # bas: grondtoon op de zware tel, kwint als afterbeat
        add(_synth_note(_deg_freq(root, octave - 2), 0.9 * spb, "pluck"), bar_beat, 0.42)
        for b in range(1, bpb):
            step_deg = root + (4 if b % 2 else 0)
            add(_synth_note(_deg_freq(step_deg, octave - 2), 0.45 * spb, "pluck"),
                bar_beat + b, 0.26)
        if kick:
            for b in (0, 2) if bpb == 4 else (0,):
                add(_kick(buf.size), bar_beat + b, 0.5)
        if hat:
            for h in range(bpb * 2):
                add(_hat(rng), bar_beat + h * 0.5, 0.10 if h % 2 else 0.05)
    # slot: laatste staart terugvouwen naar het begin → naadloze loop
    buf[:SR] += buf[total:total + SR]
    buf = buf[:total]
    peak = np.max(np.abs(buf)) or 1.0
    return _to_sound(buf / peak * 0.85, 0.65)


# Per spel een eigen deuntje: (bpm, akkoorden per maat als laddergraad,
# ritme A-maten, ritme B-maten, octaaf, timbre, tik, boem, tellen per maat)
_TUNES = {
    # schil: rustig sterrenwalsje voor het titelscherm, iets lichter in de menu's
    "title": (92, [0, 3, 5, 4], [(0, 1.5, 0), (1.5, 1.5, 1), (3, 1, 2)],
              [(0, 2, 3), (2, 2, 2)], 1, "soft", False, False, 4),
    "menu": (112, [0, 5, 3, 4], [(0, 1.5, 2), (1.5, 1.5, 1)],
             [(0, 1, 3), (1, 1, 2), (2, 1, 0)], 1, "soft", False, False, 3),
    "bellen": (126, [0, 5, 3, 4],
               [(0, .5, 0), (.5, .5, 1), (1, .5, 2), (1.5, .5, 3), (2, .5, 2), (2.5, .5, 1), (3, 1, 0)],
               [(0, 1, 2), (1, .5, 1), (1.5, .5, 2), (2, 2, 3)], 1, "pluck", True, False, 4),
    "vangen": (104, [0, 3, 5, 4], [(0, 1, 3), (1, 1, 2), (2, 1, 1), (3, 1, 0)],
               [(0, 1.5, 2), (1.5, 1.5, 1), (3, 1, 0)], 1, "soft", True, False, 4),
    "mama": (100, [0, 3, 0, 4], [(0, 1, 0), (1, 1, 2), (2, 1, 1)],
             [(0, 1.5, 2), (1.5, 1.5, 0)], 1, "soft", False, False, 3),
    "aliens": (132, [0, 4, 5, 4], [(0, .5, 0), (1, .5, 3), (1.5, .5, 2), (2.5, .5, 4), (3, .5, 2)],
               [(0, .5, 2), (.5, .5, 3), (1.5, .5, 2), (2, 1, 1), (3, 1, 0)],
               1, "pluck", True, True, 4),
    "lijnen": (110, [0, 5, 3, 4], [(0, 1, 0), (1, 1, 1), (2, 1, 2), (3, 1, 1)],
               [(0, 1, 2), (1, 1, 3), (2, 2, 2)], 1, "pluck", False, False, 4),
    "draak": (120, [0, 3, 5, 4], [(0, 1.5, 0), (1.5, .5, 1), (2, 2, 3)],
              [(0, 1, 4), (1, 1, 3), (2, 2, 2)], 1, "soft", True, True, 4),
    "toverballen": (138, [0, 5, 3, 4],
                    [(0, .5, 0), (.5, .5, 2), (1, .5, 1), (1.5, .5, 2), (2, .5, 0), (2.5, .5, 2), (3, 1, 3)],
                    [(0, .5, 3), (.5, .5, 2), (1, .5, 3), (1.5, .5, 2), (2, 2, 1)],
                    1, "pluck", True, False, 4),
    "kristal": (96, [5, 3, 5, 4], [(0, 2, 0), (2, 1, 2), (3, 1, 1)],
                [(0, 1.5, 3), (1.5, 1.5, 2), (3, 1, 1)], 2, "soft", True, False, 4),
    "hooghouden": (124, [0, 4, 0, 4], [(0, .5, 0), (1, .5, 2), (1.5, .5, 3), (2, .5, 2), (3, .5, 1)],
                   [(0, .5, 3), (1, .5, 2), (2, 1, 1), (3, 1, 0)], 1, "pluck", True, True, 4),
    "dans": (128, [0, 5, 3, 4], [(0, .5, 0), (.5, .5, 0), (1, .5, 2), (2, .5, 3), (2.5, .5, 2), (3, .5, 1)],
             [(0, .5, 3), (.5, .5, 3), (1, .5, 4), (2, 1, 2), (3, 1, 0)],
             1, "pluck", True, True, 4),
    "stenen": (116, [0, 0, 4, 4], [(0, 1, 0), (1, .5, 0), (1.5, .5, 1), (2, 1, 2), (3, 1, 0)],
               [(0, 1, 2), (1, .5, 2), (1.5, .5, 3), (2, 2, 0)], 0, "pluck", False, True, 4),
    "brug": (108, [0, 3, 5, 4], [(0, .75, 0), (.75, .25, 1), (1, .75, 2), (1.75, .25, 1), (2, 1, 3), (3, 1, 2)],
             [(0, 1, 2), (1, 1, 1), (2, 2, 0)], 1, "pluck", True, False, 4),
    "rennen": (148, [0, 5, 3, 4],
               [(0, .5, 0), (.5, .5, 1), (1, .5, 2), (1.5, .5, 3), (2, .5, 2), (2.5, .5, 3), (3, .5, 4), (3.5, .5, 3)],
               [(0, .5, 2), (.5, .5, 1), (1, 1, 2), (2, .5, 1), (2.5, .5, 2), (3, 1, 0)],
               1, "pluck", True, True, 4),
}


class Sounds:
    def __init__(self) -> None:
        rng = np.random.default_rng(3)

        # prik-popjes: toon + kort 'plop' kliekje
        self.pops = []
        for f in PENTA:
            tone = _tone(f, 0.42)
            click = rng.uniform(-1, 1, int(SR * 0.02)) * np.linspace(1, 0, int(SR * 0.02)) ** 2
            tone[: click.size] += click * 0.5
            self.pops.append(_to_sound(tone, 0.55))

        # reuzenbel: lage bloop met pitch-daling
        n = int(SR * 0.5)
        t = np.arange(n) / SR
        f = 220 * np.exp(-t * 2.2) + 70
        self.bloop = _to_sound(np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, release=1.2), 0.6)

        # gouden ster: snelle glinster-arpeggio
        arp = np.zeros(int(SR * 1.1))
        for i, f in enumerate([523.25, 659.26, 784.00, 1046.5, 1318.5, 1568.0]):
            start = int(i * 0.09 * SR)
            seg = _tone(f, 0.5) * 0.7
            arp[start:start + seg.size] += seg[: arp.size - start]
        self.golden = _to_sound(arp, 0.55)

        # alien: gek 'wieee'-glijertje omhoog
        n = int(SR * 0.7)
        t = np.arange(n) / SR
        f = 380 + 620 * (t / t[-1]) ** 1.4 + 40 * np.sin(2 * np.pi * 11 * t)
        self.wheee = _to_sound(np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, release=1.6), 0.42)

        # level-fanfare: drie blije noten
        fan = np.zeros(int(SR * 1.4))
        for i, f in enumerate([392.0, 523.25, 784.0]):
            start = int(i * 0.14 * SR)
            seg = _tone(f, 0.8) * (0.8 if i < 2 else 1.0)
            fan[start:start + seg.size] += seg[: fan.size - start]
        self.fanfare = _to_sound(fan, 0.6)

        # schichtige bel schiet weg: komische boing (toon duikt en veert terug)
        n = int(SR * 0.28)
        t = np.arange(n) / SR
        f = 330 - 180 * np.sin(np.pi * t / t[-1])
        self.boing = _to_sound(np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, release=1.4), 0.5)

        # gemiste ster dooft zachtjes uit op de grond (geen drama)
        n = int(SR * 0.35)
        noise = rng.uniform(-1, 1, n)
        noise = np.convolve(noise, np.ones(48) / 48, mode="same")  # dof maken
        self.fizzle = _to_sound(noise * np.linspace(1, 0, n) ** 2, 0.22)

        # piepje van een diertje: kort vrolijk tjilpje
        n = int(SR * 0.13)
        t = np.arange(n) / SR
        f = 1150 + 250 * np.sin(2 * np.pi * 26 * t) - 300 * t / t[-1]
        self.peep = _to_sound(np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, release=0.4), 0.3)

        # hereniging met mama: twee blije nootjes ('ta-daa')
        n = int(SR * 0.8)
        tada = np.zeros(n)
        for i, fr in enumerate([659.26, 987.77]):
            start = int(i * 0.13 * SR)
            seg = _tone(fr, 0.5) * (0.75 if i == 0 else 1.0)
            tada[start:start + seg.size] += seg[: n - start]
        self.tada = _to_sound(tada, 0.55)

        # drakenvuur: donzige ruis-woesj die omlaag zakt
        n = int(SR * 0.55)
        t = np.arange(n) / SR
        noise = rng.uniform(-1, 1, n)
        noise = np.convolve(noise, np.ones(20) / 20, mode="same")
        sweep = np.sin(2 * np.pi * np.cumsum(340 * np.exp(-t * 4) + 90) / SR)
        self.whoosh = _to_sound((noise * 0.7 + sweep * 0.5) * _env(n, attack=0.03, release=1.0), 0.4)

        # rotsbonk: doffe lage klap voor Stenen kraken
        n = int(SR * 0.20)
        t = np.arange(n) / SR
        tone = np.sin(2 * np.pi * np.cumsum(95 * np.exp(-t * 13) + 42) / SR)
        knock = rng.uniform(-1, 1, n)
        knock = np.convolve(knock, np.ones(90) / 90, mode="same")
        self.thud = _to_sound((tone * 0.8 + knock * 0.6) * _env(n, attack=0.002, release=0.5), 0.55)

        # achtergrondmuziek: per spel een eigen vrolijk deuntje
        self.tunes = {name: _render_tune(*spec) for name, spec in _TUNES.items()}
        self._music_name: str | None = None

        self._ladder = 0
        self._last_pop_ms = -10_000
        self._master = 1.0
        self._music_on = True

    def _all_effects(self) -> list:
        return self.pops + [self.bloop, self.golden, self.wheee, self.fanfare,
                            self.boing, self.fizzle, self.peep, self.tada,
                            self.whoosh, self.thud]

    def set_master(self, k: float) -> None:
        """Hoofdvolume voor effecten (0.0–1.0), instelbaar via Opties."""
        self._master = k
        for snd in self._all_effects():
            snd.set_volume(k)
        self.set_music(self._music_on)

    def set_music(self, on: bool) -> None:
        self._music_on = on
        pygame.mixer.Channel(0).set_volume(0.45 * self._master if on else 0.0)

    def play_music(self, name: str) -> None:
        """Wissel het achtergronddeuntje (met een kort fade'je); zelfde naam = niks doen."""
        if name == self._music_name or name not in self.tunes:
            return
        self._music_name = name
        ch = pygame.mixer.Channel(0)
        ch.play(self.tunes[name], loops=-1, fade_ms=350)
        ch.set_volume(0.45 * self._master if self._music_on else 0.0)

    def pop(self, now_ms: int) -> None:
        if now_ms - self._last_pop_ms > 1500:
            self._ladder = 0
        self._last_pop_ms = now_ms
        self.pops[self._ladder % len(self.pops)].play()
        self._ladder += 1
