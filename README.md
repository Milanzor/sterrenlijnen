# Sterrenlijnen

Webspel voor kinderen: volg figuren van stipjes met je **wijsvinger** voor de
camera — en bij duo-figuren met **twee handen tegelijk**, elke hand zijn eigen
lijn. Alles draait lokaal in de browser (MediaPipe-handdetectie via WASM);
er wordt niets opgenomen of verstuurd.

## Spelen

**Online:** https://milanzor.github.io/sterrenlijnen/ — elke push naar
`main` deployt automatisch naar GitHub Pages (zie
`.github/workflows/deploy.yml`).

**Lokaal:**

```bash
python3 -m http.server 8080
# open http://localhost:8080 in Chrome/Chromium/Firefox en klik op Spelen
```

Elke statische webserver werkt. De camera vereist een veilige context:
`localhost` of https.

- `?demo=1` — demostand: geen camera, twee spookvingers spelen vanzelf
  (ook handig als je even wilt zien hoe het hoort).
- `?demo=1&duo=1` — demostand die meteen met een duo-figuur begint.
- Knoppen linksboven: geluid aan/uit en volledig scherm.

## Het spel

- **Eén vinger.** Alleen je wijsvingertop trekt de lijn — dat is veel
  preciezer en natuurlijker dan een hele hand. Je vinger krijgt een gloeiend
  spoor in de kleur van de lijn; een draaiend sterretje wijst steeds de
  volgende stip aan. Wild zwaaien werkt niet: je mag maar een paar stipjes
  vooruit.
- **22 figuren** in zes moeilijkheidslagen: van lijn, regenboog, golf en berg
  via vierkant, driehoek, cirkel en vlieger naar maan, huisje, ster, bliksem,
  hart, kroon, raket, ijsje, wolk, acht, vis, bloem, slak en zon.
- **Duo-figuren: twee handen tegelijk!** Gespiegelde figuren (bergen,
  regenboog, bril, ballonnen, hart, vlinder) hebben twee lijnen: links voor je
  linkervinger, rechts voor je rechtervinger, en allebei beginnen ze in het
  midden zodat je handen samen naar buiten bewegen. Eén lijn mag maar twee
  stipjes voorlopen — loop je te ver voor, dan wacht je volgende stipje
  ("wacht op je andere hand…") tot je andere hand heeft bijgehaald. Lopen ze
  samen, dan glinstert er een lijn tussen je vingers en klinken de nootjes in
  tertsen. Duo-figuren leveren extra sterren op.
- Elke stip speelt de volgende noot van een pentatonische ladder; een figuur
  af geeft een lichtstreep over de hele lijn, confetti en sterren. Om de 12
  sterren een level-fanfare. Geen game-over, alleen sterren verdienen.

## Techniek

- Los HTML/JS/CSS, geen buildstap. `@mediapipe/tasks-vision`
  (HandLandmarker, WASM + WebGL) en het handmodel zijn meegebundeld in
  `vendor/` — het spel werkt dus ook zonder internet.
- Detectie draait op ~30 Hz (videoframetempo); de cursor wordt met
  exponentiële smoothing op schermtempo (60+ fps) gladgestreken, hetzelfde
  recept als de eerdere native versie.
- Geluid is procedureel met WebAudio: pentatonische nootjes, tada's, fanfare
  en een vrolijk achtergrondloopje — geen audiobestanden.
- `js/figures.js` bevat de figurenbibliotheek (duo-figuren als
  rechterpad + spiegeling), `game.js` de spelregels (voortgang, duo-
  synchronisatie), `fx.js` de deeltjes/confetti/sporen, `hands.js` de
  camera + handdetectie, `audio.js` het geluid.

> Dit project begon als native Python/pygame-spel met dertien mini-spellen
> (LeapMove-stijl); zie de git-geschiedenis vóór de webport voor die versie.
