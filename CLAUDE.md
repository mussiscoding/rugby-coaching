# rugby-coaching

A session planner for the Finsbury Park Men's rugby coaches. Coaches build each training session from a shared library of **activities** (warm-ups, skill zones, game zones). A session is a goal at the top plus timed **blocks**, and a block can split into parallel **groups** (Forwards / Backs, stations, and so on). Players get a read-only view of the sessions coaches share with them.

The brand name is undecided and lives only in the `APP_NAME` setting. The internal slug is `rugby-coaching` everywhere, permanently (see `docs/decisions.md`, D26). Never write the brand name into code, file names or docs.

## Reference

| Doc | Read when | Update when |
|-----|-----------|-------------|
| `docs/brainstorms/2026-10-16-session-planner-brainstorm.md` | You want to know what we're building and why | The product direction changes |
| `docs/plans/2026-10-16-feat-rugby-session-planner-v1-plan.md` | Building v1: phases, schema, routes, decisions D1–D26 | You finish a task (tick it off) |
| `docs/decisions.md` | Making an architectural or product choice | Making a non-obvious decision (propose it and wait for John's confirmation first) |
| `docs/setup.md` | Running locally, deploying, rotating keys | Anything about env, setup or deploy changes |
| `docs/jots/` | Looking for what to do next | A new idea comes up, or one is done (move it to `done/`) |

## Tech stack

- **Backend:** Python 3.12, FastAPI, stdlib `sqlite3` with raw SQL, Jinja2 templates.
- **Frontend:** server-rendered pages, plain CSS (`app/static/app.css`) and vendored htmx 2.0.4 (`app/static/htmx.min.js`, committed). No build step.
- **Hosting:** systemd unit on port 8005 behind Caddy and Cloudflare on the shared Hetzner box.

```bash
.venv/bin/uvicorn app.main:app --reload --port 8005   # run locally; open /join/dev-coach
.venv/bin/python -m pytest                             # tests
```

## Project structure

```
app/
  main.py         app, middleware (session cookie, no-store, CSP), error handlers, routers
  config.py       Settings from .env; prod key checks
  db.py           schema + views, db()/tx() helpers, coach sync
  auth.py         secret links → cookie, require_viewer/require_coach/current_coach, csrf_check
  templating.py   Jinja setup, render(), asset_version(), when/nice_date filters
  activities.py   activity library queries: search, points, links, usage, 2-hour edit lock
  sessions.py     session queries: blocks, groups (splits), coaches, focus points, moves, archive
  seed_activities.py  starter activities, inserted only into an empty library
  text.py         description → headings/paragraphs/bullets; tag + video URL helpers
  timing.py       London-time helpers, clock-time layout (reflow), double-booked coaches
  routes/         access.py (join, who, healthz), home.py, activities.py, sessions.py (plan, + picker, blocks, groups, /groups/<id> run view)
  templates/      base.html + pages
  static/         app.css (club look), fonts.css + fonts/ (self-hosted Barlow; CSP blocks font CDNs), tree.svg (header watermark), app.js, htmx.min.js
tests/            conftest.py, test_access.py, test_timing.py
deploy/           systemd unit, Caddy snippet, backup timer, deploy.sh
docs/             brainstorms/, plans/, decisions.md, setup.md, jots/
```

## Key conventions

- **Default-deny routing.** Coach routes go on a router with `dependencies=[Depends(require_coach), Depends(csrf_check)]`. Player-visible routes go on a router with `require_viewer`, and only `GET /` and `GET /sessions/{id}` belong there. `tests/test_access.py` walks every route. If you add a player route on purpose, add it to `PLAYER_ALLOWED` there.
- **Every mutation** is a POST on a coach router and takes `coach: Coach = Depends(current_coach)` for attribution. Attribution is not authorisation: the secret link is the only gate.
- **Responses.** Mutations return a 303 redirect to the page, and `hx-boost` makes that feel smooth. Validation errors re-render the form with a 200, never a 4xx. HTMX fragments are only for the picker's live search.
- **DB.**
  - Open connections with `with db() as conn:` inside the endpoint, never as a `yield` dependency.
  - Wrap every write in `with tx(conn):`.
  - Read blocks and groups through the `live_blocks` / `live_groups` views.
- **Soft delete only.** Set `archived_at`; never `DELETE` content rows.
- **Player view redaction is the security boundary.** Player templates only ever receive the output of `player_projection()`, never the full session tree.
- **XSS.** Never use `|safe`. User text renders through autoescaped Jinja only.
- **No `Referrer-Policy: no-referrer` app-wide.** It makes browsers send `Origin: null`, and `csrf_check` then rejects every edit. It's set only on `/join`.
- **Frugal testing.** Tests guard only access, player-view redaction and timing maths. Don't add CRUD tests unless a real bug earns one.
- **Migrations.** None yet. The schema is `CREATE TABLE IF NOT EXISTS`. When it first needs to change, add a susyncki-style detect-and-fix `_migrate()` to `db.py`.

## Host access (maintainer-only)

The maintainer keeps host/SSH details in `../SERVER.md`, a personal file living one level above this repo on their machine. It's not part of the project and won't exist for collaborators or CI — ignore this section if that file isn't present.
