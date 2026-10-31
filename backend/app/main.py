import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .routers import analysis, auth, kontakt, report, upload, upload_links, workplace

app = FastAPI(title="Motavi API", version="0.3.0")


def pruefe_produktion(cfg=settings) -> None:
    """Refuse to start in production without the secrets that sign-in and
    upload links depend on (E.3.12 of the review on 31.10.2026)."""
    if cfg.APP_ENV != "production":
        return
    if len(cfg.JWT_SECRET.encode()) < 32:
        raise RuntimeError("JWT_SECRET fehlt oder ist kürzer als 32 Byte (Secret Manager, docs/BETRIEB.md).")
    if not cfg.PUBLIC_APP_URL.startswith("https://"):
        raise RuntimeError("PUBLIC_APP_URL fehlt (https-Adresse des Dienstes für Upload-Links).")
    if not cfg.CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS fehlt (Adresse der Website für das Kontaktformular).")


@app.on_event("startup")
def _start() -> None:
    pruefe_produktion()

_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/v1")
app.include_router(upload.router,   prefix="/api/v1")
app.include_router(upload_links.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(report.router,   prefix="/api/v1")
app.include_router(workplace.router, prefix="/api/v1")
app.include_router(kontakt.router,   prefix="/api/v1")


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


# Serve the pre-built React SPA in production.
# A catch-all route returns static files when they exist and falls back to
# index.html for client-side routes (e.g. /app, /app/dashboard/:id) so that
# deep links and hard refreshes resolve correctly.
_frontend_dist = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
)
if os.path.isdir(_frontend_dist):
    _index_html = os.path.join(_frontend_dist, "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        # API routes are handled above; never serve the SPA for them.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = os.path.normpath(os.path.join(_frontend_dist, full_path))
        if (
            full_path
            and candidate.startswith(_frontend_dist)
            and os.path.isfile(candidate)
        ):
            return FileResponse(candidate)
        return FileResponse(_index_html)
