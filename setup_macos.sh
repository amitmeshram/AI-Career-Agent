#!/usr/bin/env bash
set -euo pipefail

skip_playwright=0
if [[ "${1:-}" == "--skip-playwright" ]]; then
  skip_playwright=1
fi

step() {
  printf '\n==> %s\n' "$1"
}

require_command() {
  local name="$1"
  local hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    printf '%s was not found. %s\n' "$name" "$hint" >&2
    exit 1
  fi
}

copy_if_missing() {
  local source="$1"
  local destination="$2"
  if [[ -f "$source" && ! -e "$destination" ]]; then
    cp "$source" "$destination"
    printf 'Created %s\n' "$destination"
  fi
}

cd "$(dirname "$0")"

step "Checking prerequisites"
require_command node "Install Node.js 18 or newer from https://nodejs.org/"
require_command npm "Install npm with Node.js 18 or newer from https://nodejs.org/"
require_command python3 "Install Python 3.10 or newer from https://www.python.org/downloads/ or Homebrew."

node_major="$(node -p "Number(process.versions.node.split('.')[0])")"
if [[ "$node_major" -lt 18 ]]; then
  printf 'Node.js 18 or newer is required. Found %s.\n' "$(node --version)" >&2
  exit 1
fi

python_ok="$(python3 - <<'PY'
import sys
print("1" if sys.version_info >= (3, 10) else "0")
PY
)"
if [[ "$python_ok" != "1" ]]; then
  printf 'Python 3.10 or newer is required. Found %s.\n' "$(python3 --version)" >&2
  exit 1
fi

node --version
python3 --version

step "Creating virtual environment"
if [[ ! -x ".venv/bin/python" ]]; then
  python3 -m venv .venv
fi
venv_python="./.venv/bin/python"
if ! "$venv_python" -m pip --version >/dev/null 2>&1; then
  printf 'Virtual environment exists but pip is missing. Repairing with ensurepip...\n'
  "$venv_python" -m ensurepip --upgrade
fi
"$venv_python" -m pip --version >/dev/null

step "Installing Python dependencies"
"$venv_python" -m pip install --upgrade pip
if [[ -d "wheels" ]]; then
  "$venv_python" -m pip install --no-index --find-links wheels -r requirements.txt
  "$venv_python" -m pip install --no-index --find-links wheels -r apps/gmail-agent/requirements.txt
else
  "$venv_python" -m pip install -r requirements.txt
  "$venv_python" -m pip install -r apps/gmail-agent/requirements.txt
fi

step "Installing Node dependencies"
npm install

if [[ "$skip_playwright" -eq 0 ]]; then
  step "Installing Playwright Chromium"
  npx playwright install chromium
  "$venv_python" -m playwright install chromium
fi

step "Creating local setup files"
copy_if_missing "config/profile.example.yml" "config/profile.yml"
copy_if_missing "templates/portals.example.yml" "portals.yml"
copy_if_missing ".env.example" ".env"
copy_if_missing "modes/_profile.template.md" "modes/_profile.md"
copy_if_missing "apps/gmail-agent/.env.example" "apps/gmail-agent/.env"

mkdir -p data/gmail-agent output reports/daily jds batch/logs batch/tracker-additions

step "Validating install"
npm run doctor || printf 'Doctor reported setup items that require your private files. Continue with the next steps below.\n'
"$venv_python" run.py --help

cat <<'EOF'

Setup complete.
Next:
  1. Add your CV to cv.md
  2. Edit config/profile.yml, portals.yml, and .env
  3. Save Google OAuth credentials as apps/gmail-agent/credentials.json if using Gmail
  4. Run: ./.venv/bin/python run.py
EOF
