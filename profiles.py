"""Spelersprofielen à la LeapMove: drie sterren-op-kleur, voortgang op schijf.

Kinderen kiezen geen naam maar een kleur (zoals de LeapMove-Guardians), dus
lezen is niet nodig. Per profiel: totaal verdiende sterren, hoeveel avonturen
af zijn (= trofeeën) en bij welke etappe van het huidige avontuur ze zijn.
"""
import json
import os

import theme

PATH = os.path.join(os.path.expanduser("~/.local/share/sterrenbellen"), "profielen.json")

# kleurnaam + digigamez-kleur; index = profiel-id
STARS = [("Rode ster", theme.CORAL), ("Groene ster", theme.LIME), ("Blauwe ster", theme.SKY)]

# volumestanden voor Opties: (naam, factor)
VOLUMES = [("Uit", 0.0), ("Zacht", 0.45), ("Normaal", 1.0)]


def _fresh() -> dict:
    return {"profiles": [{"total_stars": 0, "adv_done": 0, "adv_stage": 0}
                         for _ in STARS],
            "last": 0,
            "settings": {"volume": 2, "music": True}}


def load() -> dict:
    try:
        with open(PATH) as f:
            data = json.load(f)
        base = _fresh()
        base.update({k: data[k] for k in base if k in data})
        for p in base["profiles"]:
            for k in ("total_stars", "adv_done", "adv_stage"):
                p[k] = int(p.get(k, 0))
        st = base["settings"] = dict(_fresh()["settings"], **(base.get("settings") or {}))
        st["volume"] = min(max(int(st.get("volume", 2)), 0), len(VOLUMES) - 1)
        st["music"] = bool(st.get("music", True))
        return base
    except (OSError, ValueError, KeyError, TypeError):
        return _fresh()


def save(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        tmp = PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, PATH)
    except OSError:
        pass  # niet kunnen bewaren mag het spel nooit stoppen
