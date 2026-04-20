# rdc-correlate

Correlates Kohler RDC generator **wire-protocol TLV parameters** (`0xXXXX` IDs
streaming over TCP 5253) against **Rehlko cloud API fields** to verify or
discover new parameter mappings.

When it finds new high-confidence mappings, it opens a PR on
[rdc-protocol-research](https://github.com/andrewroydshayes/rdc-protocol-research)
that updates `PARAMETERS.md` with the discoveries.

## ⚠️ Use at your own risk

This is an **unofficial, community project** — not made, endorsed, or
supported by Kohler or Rehlko. It runs on your hardware, reads packet captures
from your own network, and logs into Kohler's cloud API using **your**
credentials. **You are responsible for your install.**

**Your Rehlko credentials stay local.** The tool reads your email and password
from `/etc/kohler-correlation.env` (root-owned, chmod 600) and uses them
**only** to authenticate against Kohler's own OAuth/API endpoints — exactly
the same endpoints the official Rehlko mobile app uses. They are never
transmitted anywhere else, stored in any log, or sent to the developer. The
OAuth `CLIENT_KEY` and `API_KEY` baked into the code are the mobile app's own
public identifiers, shared by every install of the official app (see the
comment in `rdc_correlate/cloud.py`).

**Nothing else leaves your Pi.** No telemetry, no analytics, no phone-home.
Outbound network traffic is limited to: Kohler's cloud API (your existing
account), GitHub (for opening PRs on the public research repo), and apt/PyPI
for install-time package downloads.

**The source is open; read it before running it.** MIT-licensed, ~800 lines
total. If you'd rather not `curl | sudo bash`, clone the repo, read it, run
it yourself.

**No warranty.** Per the MIT license, the software is provided **"AS IS,"
without warranty of any kind**, express or implied. The authors are not liable
for any claim, damages, or other liability arising from use of this software.

**Your relationship with Kohler/Rehlko is yours.** Using Kohler's cloud API
with your own credentials for your own generator sits in a gray area of their
terms of service. The developer's position is that this is reasonable personal
use — but read Kohler's TOS yourself and make your own call. This tool makes
it easy to stop using the API at any time: it's just a Python script.

## What it does

1. Reads `kohler.sqlite` — a database populated by the rdc-proxy pcap capture
   pipeline (wire_records) and a Rehlko cloud poller (cloud_fields).
2. For every `(wire_param_id, cloud_field_path)` pair, computes Pearson r on
   time-aligned samples + a median scale ratio.
3. Emits the highest-confidence match per wire ID that clears a threshold.
4. Diffs those findings against the current `PARAMETERS.md` in
   rdc-protocol-research. New entries are bundled into a branch and opened as
   a PR for human review.

## Quick start

See **[docs/SETUP.md](docs/SETUP.md)** for the full walkthrough (it assumes a
Pi already running rdc-proxy). The short version:

```bash
curl -fsSL https://raw.githubusercontent.com/andrewroydshayes/rdc-correlate/main/install/install.sh \
  | sudo bash

# Once credentials + gh auth are set up:
sudo /opt/rdc-correlate/venv/bin/python -m rdc_correlate correlate --out /tmp/f.json
sudo /opt/rdc-correlate/venv/bin/python -m rdc_correlate publish --findings /tmp/f.json --dry-run
sudo /opt/rdc-correlate/venv/bin/python -m rdc_correlate publish --findings /tmp/f.json
```

## Subcommands

| Command | Purpose |
|---|---|
| `correlate` | Run correlation on the sqlite db; write `findings.json` |
| `publish` | Open a PR on rdc-protocol-research for new findings (+ `--dry-run`) |
| `poll` | Test Rehlko API credentials (lists homes and devices) |

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE). Provided "AS IS," without warranty. See the full disclaimer
in the [Use at your own risk](#️-use-at-your-own-risk) section above.
