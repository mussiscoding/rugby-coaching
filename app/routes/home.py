"""Home page: coaches see sessions to plan; players see what's been shared."""

from fastapi import APIRouter, Depends, Request

from app.auth import Viewer, require_viewer
from app.templating import render

# Player allowlist: everything on this router is visible to players too.
viewer = APIRouter(dependencies=[Depends(require_viewer)])


@viewer.get("/")
def home(request: Request, v: Viewer = Depends(require_viewer)):
    if v.is_coach:
        return render(request, "home_coach.html")
    return render(request, "home_player.html")
