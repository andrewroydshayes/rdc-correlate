"""Rehlko (Kohler HomeEnergy) cloud API client — OAuth2 + polling."""

import json
import os
import time
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


TOKEN_URL = "https://kohler-homeenergy.okta.com/oauth2/default/v1/token"
API_BASE = "https://api.hems.rehlko.com"
CLIENT_KEY = "MG9hMXFpY3BkYWdLaXdFekYxZDg6d3Raa1FwNlY1T09vMW9PcjhlSFJHTnFBWEY3azZJaXhtWGhINHZjcnU2TWwxSnRLUE5obXdsMEN1MGlnQkVIRg=="
API_KEY = "pgH7QzFHJx4w46fI~5Uzi4RvtTwlEXp"
OAUTH_SCOPE = "openid profile offline_access email"


def load_env(env_path):
    """Parse a shell-style env file."""
    data = {}
    p = Path(env_path)
    if not p.exists():
        return data
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


class RehlkoClient:
    def __init__(self, email, password):
        if requests is None:
            raise RuntimeError("`requests` package not installed (pip install requests)")
        self.email = email
        self.password = password
        self._access = None
        self._refresh = None
        self._expires_at = 0.0

    def login(self):
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "password",
                "username": self.email,
                "password": self.password,
                "scope": OAUTH_SCOPE,
            },
            headers={
                "Authorization": f"Basic {CLIENT_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._store_tokens(resp.json())

    def _store_tokens(self, tok):
        self._access = tok["access_token"]
        self._refresh = tok.get("refresh_token", self._refresh)
        self._expires_at = time.time() + tok.get("expires_in", 3600) - 60

    def _refresh_token(self):
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh,
                "scope": OAUTH_SCOPE,
            },
            headers={
                "Authorization": f"Basic {CLIENT_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._store_tokens(resp.json())

    def _ensure_fresh(self):
        if not self._access:
            self.login()
        elif time.time() >= self._expires_at:
            try:
                self._refresh_token()
            except Exception:
                self.login()

    def get(self, path):
        self._ensure_fresh()
        resp = requests.get(
            f"{API_BASE}{path}",
            headers={
                "Authorization": f"Bearer {self._access}",
                "X-Api-Key": API_KEY,
                "Accept": "application/json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def list_homes(self):
        return self.get("/kem/api/v3/homeowner/homes")

    def get_device(self, device_id):
        return self.get(f"/kem/api/v3/devices/{device_id}")


def flatten(obj, prefix=""):
    """Flatten nested dict / list into (path, value) tuples, path is dotted."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(flatten(v, f"{prefix}[{i}]"))
    else:
        out.append((prefix, obj))
    return out
