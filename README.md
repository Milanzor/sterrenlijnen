# Sterrenbellen

Camera-spel voor kinderen op Linux (Hyprland) met vijf handspellen en vijf
lijfspellen, over je eigen spiegelbeeld heen, in een schil naar het voorbeeld
van de LeapFrog LeapMove. In de handspellen doen alleen handen mee
(MediaPipe-handdetectie); in de lijfspellen stuurt je hele lijf
(MediaPipe-pose). Geen game-over, alleen sterren verdienen. Alles kies je
door je hand even op een keuzebel te houden.

## De schil

- **Profielen**: bij het starten kies je je ster (rood/groen/blauw, zoals de
  LeapMove-Guardians op kleur). Sterren en trofeeën worden per profiel
  bewaard in `~/.local/share/sterrenbellen/profielen.json`.
- **Avontuur**: vijf avonturen (Sterrenweide, Bloemenvallei, Kristalgrot,
  Wolkenland, Feestplaneet) van elk twee etappes met een sterrendoel; elk
  voltooid avontuur ontgrendelt het volgende en levert een trofee op, met
  confettiregen bij de uitreiking.
- **Vrij spelen**: alle tien spellen los te kiezen.
- **Trofeeën**: de prijzenkast van dit profiel.

## Starten

```bash
uv run main.py               # profielkeuze + menu's
uv run main.py bellen        # direct een spel: bellen prikken
uv run main.py vangen        # sterren vangen
uv run main.py mama          # naar mama!
uv run main.py aliens        # aliens tikken
uv run main.py lijnen        # lijnen volgen
uv run main.py draak         # vliegende draak
uv run main.py toverballen   # toverballen
uv run main.py kristal       # kristalgrot
uv run main.py hooghouden    # bellen hooghouden
uv run main.py dans          # dans!
```

- **ESC**: één stap terug (uiteindelijk stoppen), **Q**: altijd stoppen
- **F3**: fps-statistieken (in lijfspellen ook lift/buk-waarden)
- In lijfspellen kun je ook stoppen met het LeapMove-gebaar: armen gekruist
  op je schouders leggen en even vasthouden.

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

## Vliegende draak

- Lijfspel: klapwiek met je armen en de draak klimt (lift uit de neerwaartse
  polssnelheid — continu, dus een flap kan niet "missen"); armen stil omhoog
  = zweven, bukken = duiken, stap opzij en de draak schuift mee.
- Vang de sterrenboogjes die voorbij komen drijven; klap in je handen en de
  draak spuwt vuur dat knorrige onweerswolkjes in confetti laat poffen.
- Tegen een wolkje botsen mag: het moppert even en duwt je weg, geen straf.
- Onderin wuiven bloemen en gras die wegbuigen als je er laag overheen
  scheert; af en toe zoemt er een bijtje voorbij.
- Draak- en bij-sprites zijn CC0 van bevouliin.com (zie
  `assets/sprites/LICENSES.md`); wolkjes, bloemen en gras zijn procedureel.

## Toverballen

- Bovenin staat welke kleur je moet vangen ("Vang ROOD!") — stap opzij en
  vang de vallende toverballen met je handen of je hoofd.
- De goede kleur poft in sterren; een verkeerde kleur stuitert lachend weg
  ("boing"), zonder straf. Zes goede vangsten = nieuwe kleur.
- Speels kleuren leren: rood, blauw, groen, paars, roze en geel.

## Kristalgrot

- In het donker verschijnen gouden sleuteltjes: loop ernaartoe en pak ze met
  je handen of lijf (1 ster).
- "Het licht komt!": verstop je achter een van de drie doorschijnende
  kristallen voordat het zoeklicht voorbij zwaait. De hele zwaai onvindbaar
  gebleven = 2 bonussterren ("Goed verstopt!"); gezien worden geeft alleen
  een lachje.
- Per level zwaait het licht sneller en komt het vaker.

## Bellen hooghouden

- Een grote bel dwarrelt naar beneden: stuit hem omhoog met je handen of
  hoofd en tel mee — het getal op de bel telt elke stuit (1, 2, 3, 4!).
- Vier stuiten = de bel knalt in confetti (2 sterren). Op de grond gevallen?
  Zachtjes uit, nieuwe bel, geen drama.
- Klap in je handen voor een reddingszetje omhoog. Vanaf level 2 zweven er
  twee bellen tegelijk.

## Dans!

- Het alientje doet voor, jij doet na: springen, klappen, bukken, met je
  armen zwaaien of je armen omhoog.
- Elke opdracht heeft een aflopende ring; gelukt = confetti + ster, niet
  gelukt = "Bijna!" en gewoon door naar de volgende.
- Per level wordt het tempo hoger.

## Techniek

- Python 3.12 (via uv), MediaPipe HandLandmarker + PoseLandmarker, OpenCV,
  pygame-ce.
- Drie lagen, losgekoppeld: camera-capture (MJPG 1280×720 @ 30 fps),
  detectie (~30 Hz, eigen thread; per spelmodus draait óf het hand- óf het
  pose-model), renderlus (165 Hz met vsync en exponentiële smoothing).
- Lijfsignalen (klapwiek-energie, klap, sprong, bukken, armen-gekruist)
  worden in `body.py` afgeleid van de pose-landmarks, geschaald op de eigen
  lichaamsmaat zodat de afstand tot de camera niet uitmaakt.
- Indeling: `main.py` (Game/HUD/avontuurlogica), `shell.py` (menu's,
  avonturen, trofeeën), `modes_hand.py` en `modes_body.py` (de tien
  spellen), `base.py` (Mode/HandCursor), `profiles.py`, `camera.py`,
  `body.py`, `entities.py`, `theme.py`, `audio.py`.
- Bijna alle sprites en alle geluiden worden procedureel gegenereerd (numpy);
  uitzonderingen: de modellen en het Baloo 2-font in `assets/`, en twee
  CC0-spritereeksen (draak, bij) in `assets/sprites/`.
- Webcam-gotcha's worden bij het opstarten afgehandeld
  (`exposure_dynamic_framerate=0`, geen `CAP_PROP_BUFFERSIZE`).
