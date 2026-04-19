# rdc-correlate setup

End-to-end: from a Raspberry Pi already running **rdc-proxy** (pcaps + DB
populated) to a correlation workflow that opens PRs on
[rdc-protocol-research](https://github.com/andrewroydshayes/rdc-protocol-research).

## Prerequisites

- A Raspberry Pi already running **rdc-proxy** (see
  [rdc-proxy/docs/PI-SETUP.md](https://github.com/andrewroydshayes/rdc-proxy/blob/main/docs/PI-SETUP.md))
  that has been collecting pcaps for at least one engine exercise cycle (~1 week).
- A Kohler/Rehlko cloud account with access to the generator. The login is the
  same one you use at `homeenergy.rehlko.com`.
- An active GitHub account with push access to the research repo (or a fork).

## 1. Install Claude Code (optional but recommended)

If you'd like to run rdc-correlate interactively and iterate on findings with an
AI assistant, install [Claude Code](https://docs.claude.com/en/docs/claude-code)
on the Pi:

```bash
# On the Pi (or your workstation):
curl -fsSL https://claude.com/install.sh | bash
# Then log in:
claude login
```

This is optional — rdc-correlate is a plain Python CLI and runs standalone.

## 2. Install rdc-correlate

```bash
curl -fsSL https://raw.githubusercontent.com/andrewroydshayes/rdc-correlate/main/install/install.sh \
  | sudo GITHUB_OWNER=andrewroydshayes bash
```

This installs into `/opt/rdc-correlate/`, creates a venv, and apt-installs `gh`,
`tshark`, `sqlite3`, `requests`.

> **Note:** the repo is private. You'll need to authenticate with `gh auth
> login` (see step 4) *before* the installer can `git clone` the private repo.
> If the installer fails at "clone repo", run `gh auth login` then retry.

## 3. Give it your Rehlko login

rdc-correlate reads the same env file as the existing `cloud_poller.py`:

```bash
sudo tee /etc/kohler-correlation.env > /dev/null <<EOF
REHLKO_EMAIL=<your-kohler-login-email>
REHLKO_PASSWORD=<your-kohler-password>
EOF
sudo chmod 600 /etc/kohler-correlation.env
```

Verify:

```bash
sudo /opt/rdc-correlate/venv/bin/python -m rdc_correlate poll
# Expected output:
#   [poll] authenticated. 1 home(s), 1 device(s).
#     device 31643: Model20KW
```

## 4. Authenticate the GitHub CLI

Needed so rdc-correlate can `git clone` the private repo and open PRs against
rdc-protocol-research.

```bash
gh auth login --hostname github.com --git-protocol https
```

Follow the interactive prompt. Grant `repo` + `workflow` scopes.

Verify:

```bash
gh auth status     # should show ✓ Logged in
gh repo view andrewroydshayes/rdc-protocol-research
```

## 5. Run correlation

```bash
# Against the live kohler.sqlite (adjust path if different):
sudo /opt/rdc-correlate/venv/bin/python -m rdc_correlate correlate \
  --db /home/andrew/kohler_corr/kohler.sqlite \
  --out /tmp/findings.json \
  --r-threshold 0.95 \
  --min-n 30
```

This walks every (wire_param_id × cloud_field) pair in the DB, aligns by
timestamp, computes Pearson r, and writes the winners to `findings.json`.

Typical first run: 10–20 findings.

## 6. Dry-run the publish step

See what the PR would change without actually creating one:

```bash
sudo /opt/rdc-correlate/venv/bin/python -m rdc_correlate publish \
  --findings /tmp/findings.json \
  --dry-run
```

The dry-run prints a JSON result and writes the would-be `PARAMETERS.md` to a
temp dir — review it before going live.

## 7. Open the PR for real

```bash
sudo /opt/rdc-correlate/venv/bin/python -m rdc_correlate publish \
  --findings /tmp/findings.json
```

This clones rdc-protocol-research, creates a branch like
`discoveries/YYYY-MM-DD-N-new`, updates PARAMETERS.md to include a
"Machine-verified discoveries (YYYY-MM-DD)" subsection, commits, pushes, and
opens a PR. The URL is printed at the end.

Review the PR on GitHub, merge when ready, and delete the branch.

## Running on a schedule (optional)

A simple systemd timer that runs correlation once a week and opens a PR if
there are new findings — save as `/etc/systemd/system/rdc-correlate.service`
and `/etc/systemd/system/rdc-correlate.timer`:

```ini
# rdc-correlate.service
[Unit]
Description=rdc-correlate weekly discovery run

[Service]
Type=oneshot
ExecStart=/bin/sh -c '/opt/rdc-correlate/venv/bin/python -m rdc_correlate correlate --out /tmp/f.json && /opt/rdc-correlate/venv/bin/python -m rdc_correlate publish --findings /tmp/f.json'
User=andrew
```

```ini
# rdc-correlate.timer
[Unit]
Description=Weekly rdc-correlate run

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now rdc-correlate.timer
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `poll` says "No homes found" | Your Rehlko account doesn't have the generator linked. Sign into the Rehlko web UI and pair the generator first. |
| `correlate` returns 0 findings | The DB might be nearly empty. Wait for one full engine exercise cycle (~week) so there's variance to correlate against. |
| `publish` fails on `gh pr create` | Check `gh auth status`; you may need to `gh auth refresh -s repo`. |
| "no tags yet — on main" during install | First install before v0.1.0 was tagged. Harmless — will pick up tags on next install. |
