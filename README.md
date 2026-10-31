# motavi-backend

FastAPI-Backend und internes Werkzeug von Motavi: Videoanalyse (Haltungsindex auf REBA-Basis, Bewegungen), Arbeitsplatz-Steckbrief, Upload-Links für Kunden und Kontaktformular der Website.

| Thema | Dokument |
|---|---|
| Betrieb, Dienstkonto, Secrets, Umgebungsvariablen | `docs/BETRIEB.md` |
| Löschfristen, Soft Delete | `docs/LOESCHKONZEPT.md` |
| Haltungsindex und Stufen | `docs/HALTUNGSINDEX.md` |
| Scores, Empfehlung, Wirtschaftlichkeit | `docs/SCORING.md` |
| Kontaktformular | `docs/KONTAKT.md` |
| Geplanter Worker | `docs/WORKER.md` |

Lokal:

```
pip install -r backend/requirements-dev.txt
python -m pytest -q backend/tests
uvicorn backend.app.main:app --reload
cd frontend && npm ci && npm run dev
```
