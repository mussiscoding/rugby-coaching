from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import ROOT, settings
from app.timing import nice_date, when

STATIC_DIR = ROOT / "app" / "static"

templates = Jinja2Templates(directory=ROOT / "app" / "templates")


def asset_version(path: str) -> int:
    """mtime of a static file, for ?v= cache-busting."""
    try:
        return int((STATIC_DIR / path).stat().st_mtime)
    except FileNotFoundError:
        return 0


templates.env.globals["asset_version"] = asset_version
templates.env.globals["app_name"] = settings.app_name
templates.env.filters["when"] = when
templates.env.filters["nice_date"] = nice_date


def render(request: Request, name: str, status_code: int = 200, **context):
    context.setdefault("viewer", getattr(request.state, "viewer", None))
    return templates.TemplateResponse(request, name, context, status_code=status_code)

