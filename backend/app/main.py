import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .routers import analysis, auth, report, upload

app = FastAPI(title="Motavi API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/v1")
app.include_router(upload.router,   prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(report.router,   prefix="/api/v1")


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
