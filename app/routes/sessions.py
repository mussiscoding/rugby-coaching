"""Building sessions: the plan page, the + picker, blocks, and groups (splits)."""

import re
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.datastructures import FormData

from app import activities as acts
from app import sessions as ses
from app.auth import Coach, csrf_check, current_coach, require_coach
from app.config import settings
from app.db import active_coaches, db
from app.routes.activities import form_data
from app.text import render_description
from app.timing import double_booked, layout, today_london
from app.templating import render

coach = APIRouter(dependencies=[Depends(require_coach), Depends(csrf_check)])

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# --- helpers -----------------------------------------------------------------------


def _back(request: Request, session_id: int, block_id: int | None = None, undo: tuple | None = None):
    """Redirect to the plan, scrolling back to the block you were working on."""
    if block_id:
        request.session["scroll_to"] = f"block-{block_id}"
    if undo:
        request.session["undo"] = list(undo)
    return RedirectResponse(f"/sessions/{session_id}", status_code=303)


def _session_or_404(conn, session_id: int):
    session = ses.get_session(conn, session_id)
    if session is None:
        raise HTTPException(404)
    return session


def _block_or_404(conn, block_id: int):
    block = ses.get_block(conn, block_id)
    if block is None:
        raise HTTPException(404)
    return block


def _group_or_404(conn, group_id: int):
    group = ses.get_group(conn, group_id)
    if group is None:
        raise HTTPException(404)
    return group


def _duration(raw) -> int | None:
    raw = str(raw or "").strip()
    return int(raw) if raw.isdigit() and 1 <= int(raw) <= 180 else None


def _session_values(form: FormData) -> tuple[dict, list[str]]:
    values = {k: str(form.get(k) or "").strip() for k in ("date", "start_time", "goal", "notes")}
    errors = []
    try:
        date.fromisoformat(values["date"])
    except ValueError:
        errors.append("Pick a date.")
    if not TIME_RE.match(values["start_time"]):
        errors.append("Start time should look like 19:30.")
    return values, errors


def _what(form: FormData) -> tuple[int | None, str | None]:
    """An activity id, or a free-text title (e.g. 'Water break')."""
    raw = str(form.get("activity_id") or "")
    title = " ".join(str(form.get("title") or "").split()) or None
    return (int(raw) if raw.isdigit() else None), (None if raw.isdigit() else title)


# --- sessions ------------------------------------------------------------------------


@coach.get("/sessions/new")
def new_session(request: Request, coach: Coach = Depends(current_coach)):
    values = {"date": today_london().isoformat(), "start_time": settings.default_start_time, "goal": "", "notes": ""}
    return render(request, "sessions/form.html", session=None, values=values, errors=[])


@coach.post("/sessions")
def create_session(request: Request, form: FormData = Depends(form_data), coach: Coach = Depends(current_coach)):
    values, errors = _session_values(form)
    if errors:
        return render(request, "sessions/form.html", session=None, values=values, errors=errors)
    with db() as conn:
        session_id = ses.create_session(conn, values["date"], values["start_time"], values["goal"], coach.id)
    return RedirectResponse(f"/sessions/{session_id}", status_code=303)


@coach.get("/sessions/{session_id}")
def show_session(request: Request, session_id: int):
    with db() as conn:
        session = _session_or_404(conn, session_id)
        blocks = ses.load(conn, session_id)
    plan = layout([b["duration_min"] for b in blocks], session["start_time"])
    for block, timing in zip(blocks, plan["blocks"]):
        block["timing"] = timing
        clash = double_booked(block["groups"])
        block["clash_names"] = sorted({c["name"] for g in block["groups"] for c in g["coaches"] if c["id"] in clash})
    return render(
        request, "sessions/show.html",
        session=session, blocks=blocks, plan=plan, types=acts.TYPES,
        is_past=session["date"] <= today_london().isoformat(),
        scroll_to=request.session.pop("scroll_to", None),
        undo=request.session.pop("undo", None),
    )


@coach.get("/sessions/{session_id}/edit")
def edit_session(request: Request, session_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        session = _session_or_404(conn, session_id)
    return render(request, "sessions/form.html", session=session, values=dict(session), errors=[])


@coach.post("/sessions/{session_id}")
def save_session(request: Request, session_id: int, form: FormData = Depends(form_data),
                 coach: Coach = Depends(current_coach)):
    values, errors = _session_values(form)
    with db() as conn:
        session = _session_or_404(conn, session_id)
        if errors:
            return render(request, "sessions/form.html", session=session, values=values, errors=errors)
        ses.update_session(conn, session_id, values, coach.id)
    return RedirectResponse(f"/sessions/{session_id}", status_code=303)


def next_same_weekday(source: str) -> str:
    """Next occurrence of the source session's weekday, today or later (D12)."""
    today = today_london()
    ahead = (date.fromisoformat(source).weekday() - today.weekday()) % 7
    return (today + timedelta(days=ahead)).isoformat()


@coach.get("/sessions/{session_id}/copy")
def copy_form(request: Request, session_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        session = _session_or_404(conn, session_id)
    return render(request, "sessions/copy.html", session=session, new_date=next_same_weekday(session["date"]), errors=[])


@coach.post("/sessions/{session_id}/copy")
def copy_session(request: Request, session_id: int, form: FormData = Depends(form_data),
                 coach: Coach = Depends(current_coach)):
    new_date = str(form.get("date") or "")
    with db() as conn:
        session = _session_or_404(conn, session_id)
        try:
            date.fromisoformat(new_date)
        except ValueError:
            return render(request, "sessions/copy.html", session=session, new_date=new_date, errors=["Pick a date."])
        new_id = ses.copy_session(conn, session_id, new_date, coach.id)
    return RedirectResponse(f"/sessions/{new_id}", status_code=303)


@coach.get("/deleted")
def deleted(request: Request):
    with db() as conn:
        rows = ses.recently_deleted(conn)
    return render(request, "deleted.html", rows=rows)


@coach.post("/sessions/{session_id}/archive")
def archive_session(session_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        _session_or_404(conn, session_id)
        ses.set_session_archived(conn, session_id, True, coach.id)
    return RedirectResponse(f"/sessions/{session_id}", status_code=303)


@coach.post("/sessions/{session_id}/restore")
def restore_session(session_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        _session_or_404(conn, session_id)
        ses.set_session_archived(conn, session_id, False, coach.id)
    return RedirectResponse(f"/sessions/{session_id}", status_code=303)


# --- the + picker ------------------------------------------------------------------------


@coach.get("/sessions/{session_id}/add")
def picker(request: Request, session_id: int, block_id: int | None = None, q: str = "", type: str = ""):
    """Pick an activity for a new block, or (with block_id) a new group in a split."""
    with db() as conn:
        session = _session_or_404(conn, session_id)
        block = _block_or_404(conn, block_id) if block_id else None
        results = acts.search(conn, q.strip(), type)
        suggested = []
        if not q and not type:
            seen = set()
            for aid in ses.previous_activity_ids(conn, session_id, block_id):
                for r in acts.related(conn, aid):
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        suggested.append(r)
    return render(
        request, "sessions/picker.html",
        session=session, block=block, results=results, suggested=suggested,
        q=q, type=type, types=acts.TYPES,
    )


@coach.get("/sessions/{session_id}/add/{activity_id}")
def picker_preview(request: Request, session_id: int, activity_id: int, block_id: int | None = None):
    with db() as conn:
        session = _session_or_404(conn, session_id)
        block = _block_or_404(conn, block_id) if block_id else None
        activity = acts.get(conn, activity_id)
        if activity is None or activity["archived_at"]:
            raise HTTPException(404)
        points = acts.points(conn, activity_id)
    return render(
        request, "sessions/preview.html",
        session=session, block=block, activity=activity, points=points,
        type_label=acts.TYPES[activity["type"]], description=render_description(activity["description"]),
        duration=activity["default_duration_min"] or 10,
    )


# --- blocks ------------------------------------------------------------------------------


@coach.post("/sessions/{session_id}/blocks")
def add_block(request: Request, session_id: int, form: FormData = Depends(form_data),
              coach: Coach = Depends(current_coach)):
    activity_id, title = _what(form)
    duration = _duration(form.get("duration"))
    with db() as conn:
        _session_or_404(conn, session_id)
        if (activity_id is None and not title) or duration is None:
            return RedirectResponse(f"/sessions/{session_id}/add", status_code=303)
        block_id = ses.add_block(conn, session_id, duration, activity_id, title, coach.id)
    return _back(request, session_id, block_id)


@coach.post("/blocks/{block_id}")
def set_duration(request: Request, block_id: int, form: FormData = Depends(form_data),
                 coach: Coach = Depends(current_coach)):
    with db() as conn:
        block = _block_or_404(conn, block_id)
        duration = _duration(form.get("duration"))
        if duration:
            ses.set_duration(conn, block, duration, coach.id)
    return _back(request, block["session_id"], block_id)


@coach.post("/blocks/{block_id}/move")
def move_block(request: Request, block_id: int, form: FormData = Depends(form_data),
               coach: Coach = Depends(current_coach)):
    with db() as conn:
        block = _block_or_404(conn, block_id)
        ses.move_block(conn, block, "up" if form.get("dir") == "up" else "down", coach.id)
    return _back(request, block["session_id"], block_id)


@coach.post("/blocks/{block_id}/groups")
def add_group(request: Request, block_id: int, form: FormData = Depends(form_data),
              coach: Coach = Depends(current_coach)):
    activity_id, title = _what(form)
    with db() as conn:
        block = _block_or_404(conn, block_id)
        if activity_id is not None or title:
            ses.add_group(conn, block, activity_id, title, coach.id)
    return _back(request, block["session_id"], block_id)


@coach.post("/blocks/{block_id}/archive")
def archive_block(request: Request, block_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        block = _block_or_404(conn, block_id)
        ses.set_archived(conn, "blocks", block_id, block["session_id"], True, coach.id)
    return _back(request, block["session_id"], undo=("blocks", block_id))


@coach.post("/blocks/{block_id}/restore")
def restore_block(request: Request, block_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        block = conn.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
        if block is None:
            raise HTTPException(404)
        ses.set_archived(conn, "blocks", block_id, block["session_id"], False, coach.id)
    return _back(request, block["session_id"], block_id)


# --- groups --------------------------------------------------------------------------------


@coach.get("/groups/{group_id}/edit")
def edit_group(request: Request, group_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        group = _group_or_404(conn, group_id)
        chosen = ses.group_coach_ids(conn, group_id)
        coaches = [c for c in conn.execute("SELECT id, name, active FROM coaches ORDER BY name")
                   if c["active"] or c["id"] in chosen]
        starred, custom = ses.group_focus(conn, group_id)
        points = acts.points(conn, group["activity_id"])["coaching"] if group["activity_id"] else []
        siblings = conn.execute("SELECT COUNT(*) FROM live_groups WHERE block_id = ?", (group["block_id"],)).fetchone()[0]
        labels = ses.used_labels(conn)
    return render(
        request, "sessions/group_form.html",
        group=group, coaches=coaches, chosen=chosen, points=points, starred=starred,
        custom="\n".join(custom), is_split=siblings > 1, labels=labels,
        is_past=group["session_date"] <= today_london().isoformat(),
    )


@coach.post("/groups/{group_id}")
def save_group(request: Request, group_id: int, form: FormData = Depends(form_data),
               coach: Coach = Depends(current_coach)):
    with db() as conn:
        group = _group_or_404(conn, group_id)
        valid_coaches = {c["id"] for c in conn.execute("SELECT id FROM coaches")}
        valid_points = {p["id"] for p in acts.points(conn, group["activity_id"])["coaching"]} if group["activity_id"] else set()
        values = {
            "label": " ".join(str(form.get("label") or "").split()),
            "title": (" ".join(str(form.get("title") or "").split()) or group["title"]) if not group["activity_id"] else None,
            "why_today": str(form.get("why_today") or "").strip(),
            "how_it_went": str(form.get("how_it_went") or "").strip(),
        }
        coach_ids = [int(c) for c in form.getlist("coach_id") if str(c).isdigit() and int(c) in valid_coaches]
        point_ids = [int(p) for p in form.getlist("point_id") if str(p).isdigit() and int(p) in valid_points]
        custom = [" ".join(line.split()) for line in str(form.get("custom_points") or "").splitlines() if line.strip()]
        ses.save_group(conn, group, values, coach_ids, point_ids, custom, coach.id)
    return _back(request, group["session_id"], group["block_id"])


@coach.post("/groups/{group_id}/archive")
def archive_group(request: Request, group_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        group = _group_or_404(conn, group_id)
        siblings = conn.execute("SELECT COUNT(*) FROM live_groups WHERE block_id = ?", (group["block_id"],)).fetchone()[0]
        if siblings == 1:  # last group: remove the whole block rather than leave an empty slot
            ses.set_archived(conn, "blocks", group["block_id"], group["session_id"], True, coach.id)
            return _back(request, group["session_id"], undo=("blocks", group["block_id"]))
        ses.set_archived(conn, "block_groups", group_id, group["session_id"], True, coach.id)
    return _back(request, group["session_id"], group["block_id"], undo=("block_groups", group_id))


@coach.post("/groups/{group_id}/restore")
def restore_group(request: Request, group_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        row = conn.execute(
            "SELECT g.id, g.block_id, b.session_id FROM block_groups g JOIN blocks b ON b.id = g.block_id WHERE g.id = ?",
            (group_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(404)
        ses.set_archived(conn, "block_groups", group_id, row["session_id"], False, coach.id)
    return _back(request, row["session_id"], row["block_id"])
