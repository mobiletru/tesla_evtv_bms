#!/bin/sh
set -e

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (HA SSH terminal)."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPO="mobiletru/tesla_evtv_bms"
TOKEN_FILE="/root/.github-token"
BRANCH="${BRANCH:-$(git symbolic-ref --short HEAD 2>/dev/null || echo main)}"

if [ ! -f "$TOKEN_FILE" ] && [ -z "$GITHUB_TOKEN" ]; then
  echo "No GitHub token found."
  echo "  echo 'ghp_...' > $TOKEN_FILE && chmod 600 $TOKEN_FILE"
  exit 1
fi

chmod +x scripts/github-credential.sh
git remote set-url origin "https://github.com/${REPO}.git"
git config credential.helper "$ROOT/scripts/github-credential.sh"
git config branch."$BRANCH".remote origin
git config branch."$BRANCH".merge "refs/heads/${BRANCH}"

echo "Pushing to https://github.com/$REPO (branch: $BRANCH)..."
git push -u origin "$BRANCH"
echo "Pushed to https://github.com/$REPO (branch: $BRANCH)"