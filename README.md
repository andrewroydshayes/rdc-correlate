# rdc-correlate

Correlates Kohler RDC generator **wire-protocol TLV parameters** (`0xXXXX` IDs
streaming over TCP 5253) against **Rehlko cloud API fields** to verify or
discover new parameter mappings.

When it finds new high-confidence mappings, it opens a PR on
[rdc-protocol-research](https://github.com/andrewroydshayes/rdc-protocol-research)
that updates `PARAMETERS.md` with the discoveries.

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

MIT.
