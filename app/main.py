import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.auth import NeedsCoachName, NotForPlayers, NotJoined, RedactJoinKeys, who_url
from app.config import check_prod_settings, settings
from app.db import init_db, sync_coaches
from app.seed_activities import seed_if_empty
from app.routes import access, activities, home, sessions
from app.templating import STATIC_DIR, render

logging.getLogger("uvicorn.access").addFilter(RedactJoinKeys())

CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_prod_settings(settings)
    init_db()
    sync_coaches(settings.coach_names)
    seed_if_empty()
    yield


class HeadersMiddleware(BaseHTTPMiddleware):
    """No caching of pages (Cloudflare respects origin headers) + CSP."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = CSP
        return response


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(HeadersMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="rc_session",
    max_age=365 * 24 * 3600,
    same_site="lax",
    https_only=settings.https_only,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(NotJoined)
def not_joined(request: Request, exc: NotJoined):
    return render(request, "not_joined.html", status_code=401, viewer=None)


@app.exception_handler(NotForPlayers)
def not_for_players(request: Request, exc: NotForPlayers):
    return render(request, "not_found.html", status_code=404)


@app.exception_handler(NeedsCoachName)
def needs_coach_name(request: Request, exc: NeedsCoachName):
    return RedirectResponse(who_url(exc.next_path), status_code=303)


@app.exception_handler(StarletteHTTPException)
def http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return render(request, "not_found.html", status_code=404)
    return render(request, "error.html", status_code=exc.status_code, message=exc.detail)


app.include_router(access.public)
app.include_router(access.coach)
app.include_router(home.viewer)
app.include_router(activities.coach)
app.include_router(sessions.viewer)
app.include_router(sessions.coach)
