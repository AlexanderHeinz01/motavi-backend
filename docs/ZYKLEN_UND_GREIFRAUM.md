# Zykluserkennung und Greifraum (S2)

Stand: 30.10.2026. Umsetzung von `docs/STECKBRIEF_MODUL.md` Abschnitt 4.1 und 4.2 (Repo `motavi`) in `backend/app/services/workplace/cycles.py` und `reach.py`. Eingabe sind die vorverarbeiteten Pose-Daten (`preprocess.prepare`, siehe `docs/POSE_DATEN.md`).

## Zykluserkennung (`cycles.py`)

**Merkmale je Bild:** beide Handgelenke (x, y relativ zur Hüftmitte, in Rumpflängen), Rumpfneigung und Schulterbreite (ändert sich, wenn sich der Rumpf dreht). Jeder Kanal wird standardisiert.

**Verfahren:**
1. **Periode:** Autokorrelation je Kanal, nur über Bildpaare mit erkannter Person. Die Kanäle werden danach gewichtet, wie stark sie sich bewegen (Betrag der Autokorrelation bei 0,5 s und 1 s). Eine ruhende Hand, die nur rauscht, verdünnt so nicht die Periode der arbeitenden Hand. Gesucht wird im Bereich 1,5 bis 180 s (Untergrenze am 30.10.2026 von 3 s gesenkt, weil ein echtes Video einen Zyklus von 2,8 s zeigte); es müssen mindestens drei Perioden in die Aufnahme passen. Gewählt wird der erste Gipfel, der mindestens 85 % des höchsten erreicht, damit Oberschwingungen nicht die halbe Periode liefern.
2. **Zyklusgrenzen:** Das Fenster einer Periodenlänge, das sich am besten wiederholt, wird zur Vorlage. Eine normierte Kreuzkorrelation (je Kanal, gewichtet) findet ihre Wiederholungen. Der Mittelwert der gefundenen Zyklen wird zur verfeinerten Vorlage, und die Suche läuft noch einmal. Bei langen Zyklen werden die Merkmale vorher über etwa 1/40 der Periode geglättet.
3. **Ausreißer:** Ein Abstand über 135 % des Medians wird geteilt in einen typischen Zyklus und eine **Unterbrechung** (Pause, Nebentätigkeit). Unter 65 % heißt „zu kurz“, eine Ähnlichkeit zur Vorlage unter 0,5 „weicht vom typischen Ablauf ab“, fehlende Bilder „Lücke in den Daten“. Ausreißer zählen nicht für die Zykluszeit.

**Ausgabe:** Liste der Zyklen und Unterbrechungen; Zykluszeit als Median, Mittelwert, Standardabweichung und Variationskoeffizient; Zyklen pro Schicht (hochgerechnet aus der Aufnahmedauer mit Person); Zeitanteil in Zyklen; Konfidenz.

**Qualität (Leitplanke 3):** Die Konfidenz ist das geometrische Mittel aus Periodizität, mittlerer Ähnlichkeit der Zyklen, Anteil gültiger Zyklen und Anteil der Bilder mit Person. Jede Kennzahl ist eine `Kennzahl` mit Wert, Qualität und `belastbar`. Unter 0,5 steht „nicht belastbar messbar“ statt eines Werts. Der Variationskoeffizient braucht mindestens fünf gültige Zyklen.

**Fallback:** „Kein wiederkehrender Zyklus erkannt“, wenn keine Periode gefunden wird, weniger als drei gültige Zyklen bleiben oder zu wenige Bilder eine Person zeigen („Zu wenig Bilder mit erkannter Person“). Das ist ein Ergebnis und fließt in die Empfehlung ein.

**Bekannte Grenzen:**
- Die Vorlage beginnt an einer beliebigen Stelle im Ablauf. Am Anfang und Ende der Aufnahme liegen deshalb meist Teilzyklen, die nicht zählen.
- Ein Zyklus, der auch nur kurz in eine Datenlücke reicht, gilt als Lücke.
- Die Grenzen liegen dort, wo sich der Ablauf wiederholt, nicht zwingend am fachlichen Anfang („Greifen“). Das ordnen die Ablaufschritte (S3) zu.

## Greifraum (`reach.py`)

- **Höhenzonen** je Bild und Hand mit den Körperpunkten der Person als Grenzen: unter Knie, Knie bis Hüfte, Hüfte bis Schulter, über Schulter. Anteile über beide Hände.
- **Griffe:** Die Hand kommt nach einer Bewegung zur Ruhe (unter 0,4 Rumpflängen pro Sekunde für mindestens 0,2 s, vorher innerhalb 1 s mindestens 1,0 Rumpflängen pro Sekunde). Ein Griff liegt **außerhalb des günstigen Greifraums**, wenn er nicht zwischen Hüfte und Schulter liegt oder waagerecht mehr als 0,7 Rumpflängen von der Schultermitte entfernt ist.
- **Dichte** der Handpositionen auf einem Raster über der Silhouette (für die Greifraum-Grafik).
- **Qualität:** Anteil der Bilder mit beiden Handgelenken; der Anteil der Griffe außerhalb braucht mindestens 10 erkannte Griffe.
- **Hinweis** im Ergebnis: „Relative Werte aus 2D-Video. Für Zentimeterangaben ist eine Referenzmessung vor Ort nötig.“

**Verdeckte Körperteile:** In Seitenansicht ist die abgewandte Hand oft verdeckt. Eine Hand, die in weniger als 60 % der Bilder mit Person sichtbar ist, bleibt bei Höhenzonen und Griffen außen vor; bei der Zykluserkennung fällt ihr Kanal heraus, statt alle Bilder ungültig zu machen. Verdeckte Knie (z.B. hinter einer Werkbank) werden durch die typische Proportion ersetzt (Knie 0,9 Rumpflängen unter der Hüfte). Die Qualität ist der Anteil der Bilder mit Person mal der Sichtbarkeit der verwendeten Hände.

**Bekannte Grenzen:** Ein Griff in Richtung Kamera wirkt kürzer (2D). Eine Hand, die nach einer Bewegung kurz ruht, zählt als Griff, auch wenn sie nichts greift; die Ablaufschritte (S3) trennen das später.

Alle Schwellen stehen in `CycleConfig` und `ReachConfig`. Mit Phase S4 wandern sie in `config/workplace_scoring.json`.

## Diagramm für ein Video

```
pip install -r backend/requirements-dev.txt
python -m backend.scripts.plot_cycles VIDEO.mp4 --out zyklen.png
python -m backend.scripts.plot_cycles pose.npz --out zyklen.png
```

Läuft lokal, lädt nichts hoch. Zeigt das Merkmalssignal mit Zyklen, Ausreißern und Unterbrechungen, die Autokorrelation, die Zyklusdauern und die Kennzahlen mit Qualität.

## Tests

`backend/tests/test_cycles.py` (bekannte Perioden 1,5 bis 150 s mit Rauschen, schwankende Zykluslänge, Pause, Datenlücke, zwei ähnliche Teilbewegungen, eine arbeitende Hand unter Rauschkanälen, aperiodische Bewegung, Stillstand, zu wenige Zyklen, Qualitätsschwelle) und `backend/tests/test_reach.py`. Zielwert der Abnahme: synthetische Perioden auf ±5 %.
