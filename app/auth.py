"""Access: two secret links, a signed cookie, and coach attribution.

- `/join/<key>` turns a secret link into a signed session cookie holding the
  role ("coach" | "player") and a fingerprint of the key (D4). Every request
  re-checks the fingerprint, so changing a key in `.env` logs out old links.
- Coaches pick who they are once per device (`/who`); the coach id lives in
  the same cookie (D5). This is attribution, NOT authorisation: any coach can
  pick any name. The secret link is the only gate.
- Default-deny: coach routers carry `require_coach`, the player allowlist
  carries `require_viewer`, and tests/test_access.py walks every route.
"""

import hashlib
import hmac
import logging
from dataclasses import dataclass
from urllib.parse import quote

from fastapi import HTTPException, Request

from app.config import settings
from app.db import db

ROLE_KEYS = {"coach": lambda: settings.coach_key, "player": lambda: settings.player_key}


@dataclass(frozen=True)
class Coach:
    id: int
    name: str


@dataclass(frozen=True)
class Viewer:
    role: str  # "coach" | "player"
    coach: Coach | None = None

    @property
    def is_coach(self) -> bool:
        return self.role == "coach"


class NotJoined(Exception):
    """No valid secret-link cookie. Rendered as 'Ask your coach for the link'."""


class NotForPlayers(Exception):
    """A player hit a coach-only route. Rendered as a plain 404."""


class NeedsCoachName(Exception):
    """A coach tried to change something before picking who they are."""

    def __init__(self, next_path: str):
        self.next_path = next_path


def fingerprint(key: str) -> str:
    return hmac.new(settings.secret_key.encode(), key.encode(), hashlib.sha256).hexdigest()[:16]


def role_for_key(key: str) -> str | None:
    for role, get_key in ROLE_KEYS.items():
        if hmac.compare_digest(key.encode(), get_key().encode()):
            return role
    return None


def load_viewer(request: Request) -> Viewer | None:
    """Read and validate the session cookie. Clears it if the key has changed."""
    session = request.session
    role = session.get("role")
    if role not in ROLE_KEYS:
        return None
    if not hmac.compare_digest(session.get("kf", ""), fingerprint(ROLE_KEYS[role]())):
        session.clear()
        return None
    coach = None
    coach_id = session.get("coach_id")
    if role == "coach" and coach_id is not None:
        with db() as conn:
            row = conn.execute(
                "SELECT id, name FROM coaches WHERE id = ? AND active = 1", (coach_id,)
            ).fetchone()
        if row:
            coach = Coach(id=row["id"], name=row["name"])
        else:
            session.pop("coach_id", None)
    return Viewer(role=role, coach=coach)


def join(request: Request, key: str) -> bool:
    """Apply a secret link to the session. Returns False for an unknown key.

    A coach cookie is never downgraded by the player link: coaches who tap the
    player link they just posted stay coaches (they have "View as player").
    """
    role = role_for_key(key)
    if role is None:
        return False
    current = load_viewer(request)
    if current and current.is_coach and role == "player":
        return True
    coach_id = request.session.get("coach_id") if role == "coach" else None
    request.session.clear()
    request.session.update({"role": role, "kf": fingerprint(key)})
    if coach_id is not None:
        request.session["coach_id"] = coach_id
    return True


# --- dependencies -----------------------------------------------------------


def require_viewer(request: Request) -> Viewer:
    viewer = load_viewer(request)
    if viewer is None:
        raise NotJoined()
    request.state.viewer = viewer
    return viewer


def require_coach(request: Request) -> Viewer:
    viewer = require_viewer(request)
    if not viewer.is_coach:
        raise NotForPlayers()
    return viewer


def current_coach(request: Request) -> Coach:
    """The coach making a change. Redirects to /who if they haven't picked."""
    viewer = require_coach(request)
    if viewer.coach is None:
        raise NeedsCoachName(_referer_path(request))
    return viewer.coach


def _url_host(value: str) -> str:
    if "://" in value:
        value = value.split("://", 1)[1]
    return value.split("/", 1)[0]


def csrf_check(request: Request) -> None:
    """Reject mutating requests whose Origin (or Referer) host isn't ours.

    Copied from susyncki. Never set `Referrer-Policy: no-referrer` app-wide:
    browsers then send `Origin: null` and every edit fails this check.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    host = request.headers.get("host", "")
    origin = request.headers.get("origin")
    if origin:
        if _url_host(origin) != host:
            raise HTTPException(403, "cross-origin request rejected")
        return
    referer = request.headers.get("referer", "")
    if not referer or _url_host(referer) != host:
        raise HTTPException(403, "missing or cross-origin referer")


# --- redirects ---------------------------------------------------------------


def safe_next(value: str | None) -> str:
    """Only allow same-site relative paths (no //evil.com, no /\\evil.com)."""
    if not value or not value.startswith("/") or value.startswith(("//", "/\\")):
        return "/"
    return value


def _referer_path(request: Request) -> str:
    referer = request.headers.get("referer", "")
    if "://" in referer:
        rest = referer.split("://", 1)[1]
        path = "/" + rest.split("/", 1)[1] if "/" in rest else "/"
        if _url_host(referer) == request.headers.get("host", ""):
            return safe_next(path)
    return "/"


def who_url(next_path: str) -> str:
    return "/who?next=" + quote(safe_next(next_path), safe="/")


# --- logging -----------------------------------------------------------------


class RedactJoinKeys(logging.Filter):
    """Keep secret keys out of uvicorn access logs (and so out of journalctl)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(_redact(a) for a in record.args)
        return True


def _redact(value):
    if isinstance(value, str) and "/join/" in value:
        return value.split("/join/", 1)[0] + "/join/REDACTED"
    return value
