# Setup

## Running locally

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8005
```

- **Coach view:** open http://127.0.0.1:8005/join/dev-coach
- **Player view:** open http://127.0.0.1:8005/join/dev-player in a private window

The database is created at `data/rugby-coaching.db` on first start. Delete it to start fresh.

## Environment variables

Each machine's `.env` is its environment; there's no global "prod mode" switch.

| Variable | Local | Prod |
|---|---|---|
| `COACH_KEY` | `dev-coach` | Generated secret (see below) |
| `PLAYER_KEY` | `dev-player` | Generated secret, different from the coach key |
| `SECRET_KEY` | `dev-secret-change-me` | Generated secret; signs the session cookie |
| `HTTPS_ONLY` | `false` | `true`; marks the cookie `Secure` and turns on the startup key checks |
| `APP_NAME` | anything | The display name; the only place the brand lives |
| `COACHES` | `John,Coach Two,…` | The real coach names, comma-separated |
| `DEFAULT_START_TIME` | `19:30` | Training start time |

Generate a prod secret with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

When `HTTPS_ONLY=true`, the app refuses to start if any key is shorter than 20 characters, is a dev default, or the coach and player keys match.

### Coaches

On startup, any name in `COACHES` that isn't in the `coaches` table yet gets added. Names are never removed. When someone leaves, deactivate them so their name stays on past sessions:

```bash
sqlite3 /srv/rugby-coaching/data/rugby-coaching.db "UPDATE coaches SET active = 0 WHERE name = 'Sam'"
```

## The secret links

- **Coach link:** `https://rugby-coaching.johng.me/join/<COACH_KEY>`. Post it in the coaches' WhatsApp.
- **Player link:** `https://rugby-coaching.johng.me/join/<PLAYER_KEY>`. Post it in the players' WhatsApp.

**Rotating a link** (if one leaks): change the key in `/srv/rugby-coaching/.env`, run `systemctl restart rugby-coaching`, then post the new link. Everyone holding the old link is logged out on their next visit. Changing `SECRET_KEY` logs everyone out of both links.

**Keep keys out of logs.**
- The app redacts `/join/…` from uvicorn's access log.
- The Caddy block deliberately has **no `log` directive**; adding one would write every secret link to disk.
- Cloudflare sees URLs, which is accepted (WhatsApp is a far bigger leak surface).

## Deploying

### First time (on the box, as root)

```bash
# 1. Code + venv
git clone <repo-url> /srv/rugby-coaching        # as the deploy user for a private repo
chown -R deploy:deploy /srv/rugby-coaching
sudo -u deploy bash -lc 'cd /srv/rugby-coaching && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && mkdir -p data'

# 2. Prod .env (never committed)
sudo -u deploy cp /srv/rugby-coaching/.env.example /srv/rugby-coaching/.env   # then edit in real values
chmod 600 /srv/rugby-coaching/.env

# 3. Service
cp /srv/rugby-coaching/deploy/rugby-coaching.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now rugby-coaching

# 4. Caddy: append deploy/Caddyfile.snippet to /srv/server/Caddyfile, then
systemctl reload caddy

# 5. Nightly backup (sqlite3 .backup of data/*.db, kept 7 days)
cp /srv/rugby-coaching/deploy/project-backup@rugby-coaching.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now project-backup@rugby-coaching.timer
```

The Cloudflare DNS record for the subdomain must exist too.

### Every time after

```bash
bash deploy/deploy.sh
```

This pushes `main`, pulls on the box, installs deps, restarts the service, and checks that `/healthz` responds and the live commit matches.
