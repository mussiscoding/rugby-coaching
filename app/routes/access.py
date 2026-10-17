"""Joining via a secret link, and picking who you are."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.auth import csrf_check, join, require_coach, safe_next
from app.db import active_coaches, db
from app.templating import render

public = APIRouter()
coach = APIRouter(dependencies=[Depends(require_coach), Depends(csrf_check)])


@public.get("/healthz")
def healthz():
    return PlainTextResponse("ok")


@public.get("/join/{key}")
def join_link(request: Request, key: str):
    if not join(request, key):
        response = render(request, "not_joined.html", status_code=404, viewer=None)
    else:
        response = RedirectResponse("/", status_code=303)
    # Scoped to this response only. App-wide no-referrer breaks csrf_check.
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex"
    return response


@coach.get("/who")
def who_form(request: Request, next: str = "/"):
    with db() as conn:
        coaches = active_coaches(conn)
    return render(request, "who.html", coaches=coaches, next=safe_next(next))


@coach.post("/who")
def who_pick(request: Request, coach_id: int = Form(...), next: str = Form("/")):
    with db() as conn:
        if not any(c["id"] == coach_id for c in active_coaches(conn)):
            return RedirectResponse("/who", status_code=303)
    request.session["coach_id"] = coach_id
    return RedirectResponse(safe_next(next), status_code=303)
