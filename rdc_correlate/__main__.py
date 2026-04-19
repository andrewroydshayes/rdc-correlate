"""CLI for rdc-correlate.

Usage:
  python -m rdc_correlate correlate [--db PATH] [--from-pcap DIR] [--out findings.json]
  python -m rdc_correlate publish --findings findings.json [--dry-run]
  python -m rdc_correlate poll  # run the Rehlko poller (for side-by-side capture)
"""

import argparse
import json
import os
import sys

from rdc_correlate.cloud import RehlkoClient, flatten, load_env
from rdc_correlate.correlate import correlate_all, group_cloud_by_path, group_wire_by_param
from rdc_correlate.db import cloud_fields_between, connect, wire_records_between
from rdc_correlate.publish import publish_findings


DEFAULT_DB = "/home/andrew/kohler_corr/kohler.sqlite"
DEFAULT_ENV = "/etc/kohler-correlation.env"


def cmd_correlate(args):
    con = connect(args.db)
    # Widen to the whole db if no window
    t0 = args.start or 0
    t1 = args.end or 2**31
    wire = group_wire_by_param(wire_records_between(con, t0, t1))
    cloud = group_cloud_by_path(cloud_fields_between(con, t0, t1))
    findings = correlate_all(
        wire, cloud, min_n=args.min_n, r_threshold=args.r_threshold,
    )
    with open(args.out, "w") as f:
        json.dump(findings, f, indent=2)
    print(f"[correlate] {len(findings)} mappings above r>={args.r_threshold} n>={args.min_n} -> {args.out}")


def cmd_publish(args):
    with open(args.findings) as f:
        findings = json.load(f)
    result = publish_findings(
        findings,
        research_repo=args.research_repo,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


def cmd_poll(args):
    env = load_env(args.env)
    email = env.get("REHLKO_EMAIL")
    password = env.get("REHLKO_PASSWORD")
    if not email or not password:
        print(f"Missing REHLKO_EMAIL/REHLKO_PASSWORD in {args.env}", file=sys.stderr)
        sys.exit(1)
    client = RehlkoClient(email, password)
    homes = client.list_homes()
    if not homes:
        print("No homes found on account", file=sys.stderr)
        sys.exit(1)
    devices = []
    for h in homes:
        devices.extend(h.get("devices", []))
    if not devices:
        print("No devices found on any home", file=sys.stderr)
        sys.exit(1)
    print(f"[poll] authenticated. {len(homes)} home(s), {len(devices)} device(s).")
    for d in devices:
        did = d.get("deviceId") or d.get("id")
        print(f"  device {did}: {d.get('name') or d.get('model')}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="rdc-correlate")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("correlate", help="Run correlation against the sqlite db")
    pc.add_argument("--db", default=DEFAULT_DB)
    pc.add_argument("--out", default="findings.json")
    pc.add_argument("--min-n", type=int, default=20)
    pc.add_argument("--r-threshold", type=float, default=0.90)
    pc.add_argument("--start", type=float, help="Unix ts lower bound")
    pc.add_argument("--end", type=float, help="Unix ts upper bound")
    pc.set_defaults(func=cmd_correlate)

    pp = sub.add_parser("publish", help="Open a PR on rdc-protocol-research with new mappings")
    pp.add_argument("--findings", default="findings.json")
    pp.add_argument("--research-repo", default="andrewroydshayes/rdc-protocol-research")
    pp.add_argument("--dry-run", action="store_true")
    pp.set_defaults(func=cmd_publish)

    po = sub.add_parser("poll", help="Test Rehlko API login + list devices")
    po.add_argument("--env", default=DEFAULT_ENV)
    po.set_defaults(func=cmd_poll)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
