#!/usr/bin/env bash
# Installer for rdc-correlate on the Pi.
# Assumes the pibox has an rdc-proxy (or rdc-local-proxy) already capturing
# pcaps and has `/etc/kohler-correlation.env` with Rehlko credentials.

set -euo pipefail

GITHUB_OWNER=${GITHUB_OWNER:-andrewroydshayes}
REPO_URL=${REPO_URL:-https://github.com/${GITHUB_OWNER}/rdc-correlate.git}
INSTALL_DIR=${INSTALL_DIR:-/opt/rdc-correlate}
BRANCH=${BRANCH:-}

if [[ -t 1 ]]; then
  G=$(printf '\033[32m'); R=$(printf '\033[31m'); Y=$(printf '\033[33m'); N=$(printf '\033[0m')
else
  G=""; R=""; Y=""; N=""
fi
PASS=(); FAIL=(); WARN=()
ok()   { PASS+=("$1"); echo "${G}✓${N} $1"; }
fail() { FAIL+=("$1"); echo "${R}✗${N} $1"; }
warn() { WARN+=("$1"); echo "${Y}!${N} $1"; }
step() { echo; echo "${G}── $1 ──${N}"; }

step "1/6  prerequisites"
[[ $EUID -ne 0 ]] && { fail "must run as root (sudo)"; exit 1; }
ok "root"
command -v apt-get >/dev/null || { fail "no apt-get"; exit 1; }
ok "apt-get present"

step "2/6  apt packages"
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  git python3 python3-pip python3-venv python3-requests tshark sqlite3 curl \
  >/dev/null
ok "installed: git python3 pip venv requests tshark sqlite3 curl"

# gh CLI for publish step
if ! command -v gh >/dev/null 2>&1; then
  step "2b/6  install GitHub CLI (gh)"
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg status=none
  chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update -qq
  apt-get install -y -qq gh >/dev/null
fi
ok "gh CLI: $(gh --version | head -1)"

step "3/6  clone repo"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" fetch --tags --quiet
  ok "repo present; fetched"
else
  git clone --quiet "$REPO_URL" "$INSTALL_DIR"
  ok "cloned $REPO_URL"
fi
if [[ -n "$BRANCH" ]]; then
  git -C "$INSTALL_DIR" checkout --quiet "$BRANCH"
  ok "on $BRANCH"
else
  LATEST=$(git -C "$INSTALL_DIR" tag --sort=-v:refname | head -1)
  if [[ -n "$LATEST" ]]; then
    git -C "$INSTALL_DIR" checkout --quiet "$LATEST"
    ok "latest tag: $LATEST"
  else
    git -C "$INSTALL_DIR" checkout --quiet main
    warn "no tags yet — on main"
  fi
fi

step "4/6  python venv"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip setuptools
"$INSTALL_DIR/venv/bin/pip" install --quiet "$INSTALL_DIR"
ok "package installed into venv"

step "5/6  credentials check"
if [[ -f /etc/kohler-correlation.env ]]; then
  ok "/etc/kohler-correlation.env exists"
  chmod 600 /etc/kohler-correlation.env || true
else
  warn "no /etc/kohler-correlation.env — create it before running 'poll':"
  warn '  sudo tee /etc/kohler-correlation.env <<EOF'
  warn '  REHLKO_EMAIL=<your-kohler-login-email>'
  warn '  REHLKO_PASSWORD=<your-kohler-password>'
  warn '  EOF'
  warn '  sudo chmod 600 /etc/kohler-correlation.env'
fi

step "6/6  gh auth check"
if gh auth status >/dev/null 2>&1; then
  ok "gh already authenticated"
else
  warn "gh not authenticated — run this once as the user who will call 'publish':"
  warn "  gh auth login"
fi

echo
echo "${G}rdc-correlate installed.${N}"
echo
echo "Try:"
echo "  sudo $INSTALL_DIR/venv/bin/python -m rdc_correlate poll"
echo "  sudo $INSTALL_DIR/venv/bin/python -m rdc_correlate correlate --out /tmp/f.json"
echo "  sudo $INSTALL_DIR/venv/bin/python -m rdc_correlate publish --findings /tmp/f.json --dry-run"

if [[ ${#FAIL[@]} -gt 0 ]]; then
  echo
  printf '%s✗%s %s\n' "$R" "$N" "${FAIL[@]}"
  exit 1
fi
