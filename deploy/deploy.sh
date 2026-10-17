#!/usr/bin/env bash
# Deploy rugby-coaching to the Hetzner box (adapted from susyncki).
#
# Usage: bash deploy/deploy.sh
#
# Pushes main to GitHub, pulls on the server as the deploy user, installs deps,
# restarts the service, checks it's up and running the same commit.
set -euo pipefail

SSH_HOST="root@46.225.17.228"
SSH_KEY="$HOME/.ssh/id_ed25519_personal"
SERVER_PATH="/srv/rugby-coaching"
SERVICE="rugby-coaching"
URL="https://rugby-coaching.johng.me"

cyan() { printf '\033[36m%s\033[0m\n' "$*"; }
red()  { printf '\033[31m%s\033[0m\n' "$*"; }

cd "$(dirname "$0")/.."

if ! git diff --quiet || ! git diff --cached --quiet; then
  red "Working tree has uncommitted changes. Commit or stash before deploying."
  git status --short
  exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
  red "On $BRANCH — only main can be deployed. Merge into main first."
  exit 1
fi
LOCAL_SHA=$(git rev-parse HEAD)

cyan "==> Pushing $BRANCH to origin"
git push origin "$BRANCH"

cyan "==> Deploying $LOCAL_SHA on $SSH_HOST"
ssh -i "$SSH_KEY" "$SSH_HOST" "
  set -e
  sudo -u deploy bash -lc '
    cd $SERVER_PATH
    git fetch --quiet origin
    git reset --hard origin/$BRANCH
    .venv/bin/pip install --quiet -r requirements.txt
  '
  systemctl restart $SERVICE
"

cyan "==> Verifying"
for path in /healthz /static/htmx.min.js /static/app.css; do
  for _ in $(seq 20); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$URL$path")
    [ "$code" = "502" ] || break
    sleep 1
  done
  printf '  %s  %s\n' "$code" "$path"
  [ "$code" = "200" ] || { red "$path returned $code"; exit 1; }
done

REMOTE_SHA=$(ssh -i "$SSH_KEY" "$SSH_HOST" "sudo -u deploy git -C $SERVER_PATH rev-parse HEAD")
if [ "$REMOTE_SHA" = "$LOCAL_SHA" ]; then
  cyan "==> Live SHA matches local: $LOCAL_SHA"
else
  red "Live SHA $REMOTE_SHA != local $LOCAL_SHA"
  exit 1
fi

cyan "==> Done"
