# Sterrenbellen

Camera-spel voor kinderen op Linux (Hyprland) met vijf spellen die je met je
handen bestuurt, over je eigen spiegelbeeld heen. Alleen handen doen mee
(MediaPipe-handdetectie), dus met je hoofd of buik gebeurt er niets. Geen
game-over, alleen sterren verdienen. Kies in het menu een spel door je hand
even op een keuzebel te houden.

## Starten

```bash
uv run main.py            # menu
uv run main.py bellen     # direct: bellen prikken
uv run main.py vangen     # direct: sterren vangen
uv run main.py mama       # direct: naar mama!
uv run main.py aliens     # direct: aliens tikken
uv run main.py lijnen     # direct: lijnen volgen
```

- **ESC**: terug naar het menu (in het menu: stoppen), **Q**: altijd stoppen
- **F3**: fps-statistieken

## Bellen prikken

- **Gewone bellen** in de zes digigamez-speelkleuren, met knipperende oogjes
  die je hand volgen en blosjes.
- **Reuzenbel** (vanaf level 2): spat uiteen in vijf mini-belletjes.
- **Schichtige bel** (vanaf level 2): schiet weg als je hand dichtbij komt
  ("boing"), en wordt na drie sprongen moe.
- **Gouden sterbel**: laat álle bellen in cascade knallen.
- **Passagiersbel**: er zit een alien in die er zwaaiend uit tolt ("wieee!").
- Elke prik speelt de volgende noot van een pentatonische ladder; om de 12
  sterren een level-fanfare met confetti. Per level: sneller, meer bellen.

## Sterren vangen

- Sterren dwarrelen naar beneden; vang ze met een **open hand** — een vuist
  vangt niets (handopenheid uit de MediaPipe-landmarks).
- **Kometen** (vanaf level 2) vallen sneller, laten een staart na en tellen
  dubbel.
- Een gemiste ster dooft zachtjes uit op de grond — geen drama.

## Naar mama!

- Drie mama-dieren (kuiken, kikker, konijn) zitten bovenin in een nest; hun
  kleintjes huppelen onderin rond en piepen af en toe.
- Houd je hand op een kleintje en het springt in je hand; breng het naar de
  juiste mama (een pulserende ring wijst de weg) voor een hartjes-hereniging
  ("ta-daa", 2 sterren). Eén diertje per hand, dus met twee handen kun je er
  twee tegelijk dragen.
- De verkeerde mama schudt vriendelijk van nee; raak je je hand kwijt, dan
  dwarrelt het diertje gewoon terug naar de grond.

## Aliens tikken

- Aliens komen over de onderrand gluren (soms alleen hun oogjes) en duiken na
  een paar tellen weer weg — tik ze met je vingers op hun hoofd ("wieee!").
- Per level: meer aliens tegelijk, korter gluren.

## Lijnen volgen

- Een figuur van stipjes verschijnt met de naam erboven; volg de stipjes met
  je vinger. 22 figuren in zes moeilijkheidslagen: van lijn, regenboog, golf
  en berg via vierkant, driehoek, cirkel, vlieger, maan, huisje, ster en
  bliksem naar hart, kroon, raket, ijsje, wolk, acht, vis, bloem, slak en
  zon. Binnen een laag is de volgorde elke keer anders; daarna gaat alles
  door elkaar.
- Elke stip die oplicht speelt de volgende noot van de pentatonische ladder;
  een draaiend sterretje wijst steeds de volgende stip aan. Wild zwaaien werkt
  niet: je mag maar een paar stipjes vooruit.
- Figuur af = confetti langs de hele lijn + 3 sterren; de ster teken je in één
  haal, zoals kinderen dat doen.

## Techniek

- Python 3.12 (via uv), MediaPipe HandLandmarker, OpenCV, pygame-ce.
- Drie lagen, losgekoppeld: camera-capture (MJPG 1280×720 @ 30 fps),
  handdetectie (~30 Hz, eigen thread), renderlus (165 Hz met vsync en
  exponentiële smoothing van de handposities).
- Alle sprites en geluiden worden procedureel gegenereerd (numpy) — geen
  asset-bestanden behalve het model en het Baloo 2-font in `assets/`.
- Webcam-gotcha's worden bij het opstarten afgehandeld
  (`exposure_dynamic_framerate=0`, geen `CAP_PROP_BUFFERSIZE`).
