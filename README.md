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
- `?letters=1` — start (met `auto`/`demo`) in de Letter leer modus;
  `?letter=b` springt naar die letter.
- Knoppen linksboven: geluid aan/uit, volledig scherm, level overslaan en
  wisselen tussen de modi.

## Twee modi

- **Level modus** — de 100 figuren hieronder, oplopend in moeilijkheid.
- **Letter leer modus** — alle 26 kleine drukletters (a t/m z) natrekken,
  haal voor haal in de échte schrijfvolgorde en -richting, zoals op school:
  cijfertjes markeren waar elke haal begint, en je trekt ze ná elkaar.
  De letters staan tussen schrijflijnen (grondlijn, x-hoogte, bovenlijn) en
  naast de schrijfregel staat de letter als voorbeeld in het kinderfont
  **Kermit** (Underware/Microsoft 365). Kermit is een commercieel font en
  kan dus niet meegebundeld worden; wie het via Microsoft 365 op zijn
  machine heeft ziet het vanzelf, anders valt het terug op Baloo 2. Bij elke
  letter wordt de naam ook uitgesproken (SpeechSynthesis, Nederlands).
  Voortgang wordt apart van de Level modus onthouden.

## Het spel

- **Eén vinger.** Alleen je wijsvingertop trekt de lijn — dat is veel
  preciezer en natuurlijker dan een hele hand. Je vinger krijgt een gloeiend
  spoor in de kleur van de lijn; een draaiend sterretje wijst steeds de
  volgende stip aan. Wild zwaaien werkt niet: je mag maar een paar stipjes
  vooruit.
- **100 unieke levels**, oplopend in moeilijkheid: van lijn, vinkje en
  regenboog via cijfers (1, 2, 3, 5, 6, 7, 9 — spelend leren schrijven),
  bootje, kasteel, paddenstoel en ufo naar klavertje vier, propeller,
  achtbaan en slak. Elke tien levels een fanfare-mijlpaal; level 100 is een
  duo-finale met twee sterren tegelijk. Daarna: vrij spelen, alles door
  elkaar. Voortgang en sterren worden lokaal onthouden (localStorage).
  Met ⏭ (linksboven) kan een level worden overgeslagen; `?level=N` springt
  direct naar een level.
- **Duo-figuren: twee handen tegelijk!** Twintig gespiegelde figuren (van bergen en
  dubbele regenboog tot kersen, kerstboom, strik, vleermuis en de
  dubbele-ster-finale) hebben twee lijnen: links voor je
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
- Detectie draait op ~30 Hz in een **Web Worker** op verkleinde frames
  (480×270): de renderlus wacht er nooit op, dus geen haperingen als het
  model even langer doet over een frame. De cursor wordt met exponentiële
  smoothing op schermtempo (60+ fps) gladgestreken.
- Tekenwerk is gierig gehouden: gloed als vooraf gerenderde sprites (geen
  gradients per frame), lijngloed met dubbele strokes in plaats van dure
  shadowBlur, en teksten uit een canvas-cache.
- Geluid is procedureel met WebAudio: pentatonische nootjes, tada's, fanfare
  en een vrolijk achtergrondloopje — geen audiobestanden.
- `js/figures.js` bevat de figurenbibliotheek (duo-figuren als
  rechterpad + spiegeling), `game.js` de spelregels (voortgang, duo-
  synchronisatie), `fx.js` de deeltjes/confetti/sporen, `hands.js` de
  camera + handdetectie, `audio.js` het geluid.

> Dit project begon als native Python/pygame-spel met dertien mini-spellen
> (LeapMove-stijl); zie de git-geschiedenis vóór de webport voor die versie.
