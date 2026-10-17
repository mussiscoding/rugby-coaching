"""The activity library: browse, read, create, edit (with the 2-hour lock), relate."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.datastructures import FormData

from app import activities as acts
from app.auth import Coach, Viewer, csrf_check, current_coach, require_coach
from app.db import db
from app.text import DESCRIPTION_TEMPLATE, normalise_tags, render_description, split_tags, valid_video_url
from app.templating import render

coach = APIRouter(dependencies=[Depends(require_coach), Depends(csrf_check)])


async def form_data(request: Request) -> FormData:
    return await request.form()


def _see(activity_id: int) -> RedirectResponse:
    return RedirectResponse(f"/activities/{activity_id}", status_code=303)


def _load(conn, activity_id: int):
    activity = acts.get(conn, activity_id)
    if activity is None:
        raise HTTPException(404)
    return activity


# --- browse & read ---------------------------------------------------------------


@coach.get("/activities")
def index(request: Request, q: str = "", type: str = "", tag: str = ""):
    with db() as conn:
        items = acts.search(conn, q.strip(), type, tag)
        tags = acts.all_tags(conn)
    return render(
        request, "activities/index.html",
        items=items, tags=tags, q=q, type=type, tag=tag, types=acts.TYPES, split_tags=split_tags,
    )


@coach.get("/activities/new")
def new_form(request: Request, coach: Coach = Depends(current_coach)):
    with db() as conn:
        tags = acts.all_tags(conn)
    values = {f: "" for f in acts.FIELDS} | {"type": "skill", "description": DESCRIPTION_TEMPLATE}
    return render(
        request, "activities/form.html",
        activity=None, values=values, point_rows={k: [] for k in acts.POINT_KINDS},
        errors=[], all_tags=tags, types=acts.TYPES, used_in=0,
    )


@coach.get("/activities/{activity_id}")
def show(request: Request, activity_id: int, v: Viewer = Depends(require_coach)):
    with db() as conn:
        activity = _load(conn, activity_id)
        related = acts.related(conn, activity_id)
        related_ids = {r["id"] for r in related} | {activity_id}
        others = [a for a in acts.search(conn) if a["id"] not in related_ids]
        context = dict(
            activity=activity,
            type_label=acts.TYPES[activity["type"]],
            tags=split_tags(activity["tags"]),
            description=render_description(activity["description"]),
            points=acts.points(conn, activity_id),
            related=related,
            others=others,
            usage=acts.usage(conn, activity_id),
            used_in=acts.sessions_using(conn, activity_id),
            locked_by=acts.lock_holder(activity, v.coach.id if v.coach else -1),
        )
    return render(request, "activities/show.html", **context)


# --- create & edit ---------------------------------------------------------------


def _parse(form: FormData) -> tuple[dict, dict, list[str]]:
    errors: list[str] = []
    values = {f: (form.get(f) or "").strip() for f in acts.FIELDS}
    values["description"] = (form.get("description") or "").replace("\r\n", "\n").strip() + "\n"
    if not values["name"]:
        errors.append("Give it a name.")
    if values["type"] not in acts.TYPES:
        errors.append("Pick a type.")
    values["tags"] = normalise_tags(values["tags"])
    if not valid_video_url(values["video_url"]):
        errors.append("The video link needs to start with https://")
    for field, label, low, high in (
        ("coaches_needed", "Coaches needed", 0, 20),
        ("default_duration_min", "Default minutes", 1, 180),
    ):
        raw = values[field]
        if raw == "":
            values[field] = None
        elif raw.isdigit() and low <= int(raw) <= high:
            values[field] = int(raw)
        else:
            errors.append(f"{label} should be a number from {low} to {high}.")

    point_rows: dict[str, list] = {}
    for kind in acts.POINT_KINDS:
        rows = []
        for raw_id, text in zip(form.getlist(f"{kind}_id"), form.getlist(f"{kind}_text")):
            text = " ".join(str(text).split())
            if text:
                rows.append((int(raw_id) if str(raw_id).isdigit() else None, text))
        point_rows[kind] = rows
    return values, point_rows, errors


def _form_again(request, conn, activity, values, point_rows, errors):
    shown = {k: [{"id": pid, "text": t} for pid, t in rows] for k, rows in point_rows.items()}
    return render(
        request, "activities/form.html",
        activity=activity, values=values, point_rows=shown, errors=errors,
        all_tags=acts.all_tags(conn), types=acts.TYPES,
        used_in=acts.sessions_using(conn, activity["id"]) if activity else 0,
    )


@coach.post("/activities")
def create(request: Request, form: FormData = Depends(form_data), coach: Coach = Depends(current_coach)):
    values, point_rows, errors = _parse(form)
    with db() as conn:
        if errors:
            return _form_again(request, conn, None, values, point_rows, errors)
        activity_id = acts.create(conn, values, point_rows, coach.id)
    return _see(activity_id)


@coach.post("/activities/{activity_id}/lock")
def lock(activity_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        _load(conn, activity_id)
        if not acts.take_lock(conn, activity_id, coach.id):
            return _see(activity_id)
    return RedirectResponse(f"/activities/{activity_id}/edit", status_code=303)


@coach.get("/activities/{activity_id}/edit")
def edit_form(request: Request, activity_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        activity = _load(conn, activity_id)
        if activity["editing_by"] != coach.id:
            return _see(activity_id)
        values = {f: activity[f] if activity[f] is not None else "" for f in acts.FIELDS}
        point_rows = {k: [dict(r) for r in rows] for k, rows in acts.points(conn, activity_id).items()}
        return render(
            request, "activities/form.html",
            activity=activity, values=values, point_rows=point_rows, errors=[],
            all_tags=acts.all_tags(conn), types=acts.TYPES,
            used_in=acts.sessions_using(conn, activity_id),
        )


@coach.post("/activities/{activity_id}")
def save(request: Request, activity_id: int, form: FormData = Depends(form_data), coach: Coach = Depends(current_coach)):
    values, point_rows, errors = _parse(form)
    with db() as conn:
        activity = _load(conn, activity_id)
        if errors:
            return _form_again(request, conn, activity, values, point_rows, errors)
        taken_by = acts.update(conn, activity_id, values, point_rows, coach.id)
        if taken_by:
            message = f"Your edit lock ran out and {taken_by} is now editing this. Your version is below — copy what you need."
            return _form_again(request, conn, activity, values, point_rows, [message])
    return _see(activity_id)


@coach.post("/activities/{activity_id}/cancel")
def cancel(activity_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        acts.release_lock(conn, activity_id, coach.id)
    return _see(activity_id)


# --- delete, restore, related -----------------------------------------------------


@coach.post("/activities/{activity_id}/archive")
def archive(activity_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        _load(conn, activity_id)
        acts.set_archived(conn, activity_id, True, coach.id)
    return _see(activity_id)


@coach.post("/activities/{activity_id}/restore")
def restore(activity_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        _load(conn, activity_id)
        acts.set_archived(conn, activity_id, False, coach.id)
    return _see(activity_id)


@coach.post("/activities/{activity_id}/links")
def add_link(activity_id: int, form: FormData = Depends(form_data), coach: Coach = Depends(current_coach)):
    other = str(form.get("other_id", ""))
    with db() as conn:
        _load(conn, activity_id)
        if other.isdigit() and acts.get(conn, int(other)):
            acts.link(conn, activity_id, int(other))
    return _see(activity_id)


@coach.post("/activities/{activity_id}/links/{other_id}/remove")
def remove_link(activity_id: int, other_id: int, coach: Coach = Depends(current_coach)):
    with db() as conn:
        acts.unlink(conn, activity_id, other_id)
    return _see(activity_id)
