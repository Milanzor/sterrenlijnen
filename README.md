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
- `?woorden=1` — idem voor de Woorden modus; `?woord=kat` springt naar
  dat woord.
- Knoppen linksboven: geluid aan/uit (M), volledig scherm (F), overslaan
  (N of →) en wisselen tussen de modi (W) — de toetsen zijn voor papa/mama,
  het kind heeft zijn handen in de lucht. Wisselen gebeurt ter plekke: camera
  en handmodel blijven draaien.

## Drie modi

- **Level modus** — de 100 figuren hieronder, oplopend in moeilijkheid.
- **Letter leer modus** — alle 26 kleine drukletters (a t/m z) natrekken,
  haal voor haal in de échte schrijfvolgorde en -richting, zoals op school:
  cijfertjes markeren waar elke haal begint, en je trekt ze ná elkaar.
  De letters staan tussen schrijflijnen (grondlijn, x-hoogte, bovenlijn) en
  naast de schrijfregel staat de letter als voorbeeld in **Playwrite NL**
  (Google/TypeTogether, OFL, meegebundeld in `assets/`): het Nederlandse
  verbonden schoolschrift met lussen, gebaseerd op het Primarium-onderzoek
  naar hoe kinderen hier leren schrijven. Elke letter krijgt een ankerwoord,
  zoals de juf het zegt: "de m van maan" — te zien bovenin en uitgesproken
  (SpeechSynthesis, met een Nederlandse stem; is die er niet, dan blijft het
  stil in plaats van een Engelse stem Nederlands te laten voorlezen).
  Het na te trekken spoor is de échte lettervorm (vloeiend, uit het font);
  de stipjes staan dicht op elkaar en het raakvlak is kleiner dan bij de
  figuren, zodat de vinger de vorm werkelijk volgt, tot het eind van de haal.
- **Woorden modus** — twintig korte klankzuivere leeswoorden (ik, aap, kat,
  vis … maan, roos, poes), samengesteld uit dezelfde letterhalen: je trekt
  het woord letter voor letter, haal voor haal, elke letter in zijn eigen
  kleur, en aan het eind wordt het woord uitgesproken.

Elke modus onthoudt zijn eigen voortgang (localStorage); met de knop
linksboven wissel je rond (Level → Letters → Woorden). De demostand slaat
niets op.

## Het spel

- **Eén vinger.** Alleen je wijsvingertop trekt de lijn — dat is veel
  preciezer en natuurlijker dan een hele hand. Je vinger krijgt een gloeiend
  spoor in de kleur van de lijn; een draaiend sterretje wijst steeds de
  volgende stip aan. Strikt op volgorde: alleen de eerstvolgende stip telt —
  stipjes verderop aanraken doet niets, dus wild zwaaien of vooruitwerken
  kan niet.
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
- **Elke stip speelt de volgende noot van een écht kinderliedje** — achttien
  melodieën (Vader Jacob, Kortjakje, Poesje mauw, Hansje Pansje, Ode an die
  Freude, Jingle Bells, When the Saints …) in een geschudde stapel: pas als
  alle liedjes geweest zijn wordt er opnieuw geschud, en nooit twee keer
  hetzelfde achter elkaar. Het ritme bepaal je zelf met je vinger. Een figuur
  af geeft een lichtstreep over de hele lijn, confetti en sterren. Om de 12
  sterren een level-fanfare. Geen game-over, alleen sterren verdienen.

## Techniek

- Los HTML/JS/CSS, geen buildstap. `@mediapipe/tasks-vision`
  (HandLandmarker, WASM + WebGL) en het handmodel zijn meegebundeld in
  `vendor/` — het spel werkt dus ook zonder internet.
- Detectie draait op ~30 Hz in een **Web Worker** op verkleinde frames
  (640×360): de renderlus wacht er nooit op, dus geen haperingen als het
  model even langer doet over een frame. Het model laadt al terwijl het
  startscherm nog staat. De cursor wordt op schermtempo (60+ fps) adaptief
  gladgestreken: stil = rustig op de stip, bewegen = direct volgen. Raken
  telt over het hele stukje dat de vinger per frame aflegt.
- Tekenwerk is gierig gehouden: camerabeeld, vignet en sterren zijn eigen
  lagen áchter het spelcanvas (de browser zet de video zelf neer), gloed als
  vooraf gerenderde sprites, lijnen als gecachete `Path2D`, lijngloed met
  dubbele strokes in plaats van dure shadowBlur, en teksten uit een
  canvas-cache op schermresolutie.
- Fonts als woff2 (`assets/PlaywriteNL.ttf` blijft staan als bron voor
  `tools/letterpaden`). Het scherm blijft wakker tijdens het spelen (Wake
  Lock) en de muziek pauzeert als het tabblad uit beeld is.
- Geluid is procedureel met WebAudio: kinderliedjes noot voor noot (audio.js
  LIEDJES, toonladder-graden in majeur), tada's, fanfare en een zachte
  bas/akkoord-puls als achtergrond — geen audiobestanden. De achtergrond
  heeft bewust geen eigen melodielijn: de melodie komt van de stipjes.
- `js/figures.js` bevat de figurenbibliotheek (duo-figuren als
  rechterpad + spiegeling), `game.js` de spelregels (voortgang, duo-
  synchronisatie), `fx.js` de deeltjes/confetti/sporen, `hands.js` de
  camera + handdetectie, `audio.js` het geluid.

> Dit project begon als native Python/pygame-spel met dertien mini-spellen
> (LeapMove-stijl); zie de git-geschiedenis vóór de webport voor die versie.
