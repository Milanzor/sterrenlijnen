"""Procedurele audio: geen bestanden, alles met numpy gesynthetiseerd.

Pops lopen een pentatonische ladder op (zoals Zeepbellen in digigamez): elke
prik is de volgende noot, na anderhalve seconde stilte begint de ladder opnieuw.
"""
import numpy as np
import pygame

SR = 44100

# C-majeur pentatonisch over twee octaven
PENTA = [261.63, 293.66, 329.63, 392.00, 440.00,
         523.25, 587.33, 659.26, 784.00, 880.00]


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

        # zachte ruimtepad-loop op de achtergrond
        n = int(SR * 8)
        t = np.arange(n) / SR
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / 8)  # naadloos over de loopgrens
        pad = (np.sin(2 * np.pi * 65.41 * t) + np.sin(2 * np.pi * 65.41 * 1.5 * t) * 0.6
               + np.sin(2 * np.pi * 65.41 * 2.02 * t) * 0.35) * (0.4 + 0.6 * lfo)
        self.pad = _to_sound(pad, 0.05)

        self._ladder = 0
        self._last_pop_ms = -10_000

    def start_ambience(self) -> None:
        ch = pygame.mixer.Channel(0)
        ch.play(self.pad, loops=-1)
        ch.set_volume(0.5)

    def pop(self, now_ms: int) -> None:
        if now_ms - self._last_pop_ms > 1500:
            self._ladder = 0
        self._last_pop_ms = now_ms
        self.pops[self._ladder % len(self.pops)].play()
        self._ladder += 1
