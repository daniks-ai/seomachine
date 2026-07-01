"""
LinkedIn OAuth helper — one-time interactive login + automatic token refresh,
so the publishing pipeline (see linkedin_publisher.py / the /daily-publish
command) can run hands-off.

WHAT THIS SOLVES
    LinkedIn access tokens expire after 60 days. This module obtains one via the
    3-legged authorization-code flow, stores it, and — when LinkedIn grants a
    refresh token — silently mints a new access token before the old one dies.

IMPORTANT: REFRESH TOKENS ARE NOT GUARANTEED
    "Programmatic refresh tokens" are a per-application entitlement that LinkedIn
    enables server-side (historically only for approved Marketing Developer
    Platform partners; sometimes for Community Management API apps). They are NOT
    controlled by any scope or request parameter. If your app is NOT entitled,
    the authorization-code exchange returns ONLY access_token/expires_in/scope —
    no refresh_token — and there is nothing you can add to the request to change
    that. This module detects that case at runtime, warns loudly, and falls back
    to asking you to re-run `login` roughly every ~57 days. To get true hands-off
    renewal, request "programmatic refresh tokens" for app 245710141 via LinkedIn
    Developer Support once the Community Management API is approved.

ONE-TIME SETUP
    1. In https://www.linkedin.com/developers/apps → your app → Auth tab:
         - copy the Client ID and Client Secret
         - add an Authorized redirect URL: http://localhost:8000/callback
           (must match LINKEDIN_REDIRECT_URI byte-for-byte)
    2. Fill these in data_sources/config/.env:
         LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET
         LINKEDIN_REDIRECT_URI   (default http://localhost:8000/callback)
         LINKEDIN_SCOPES         (default "w_organization_social r_organization_social")
         LINKEDIN_ORGANIZATION_ID
    3. Run the one-time login (opens your browser):
         python data_sources/modules/linkedin_auth.py login
    4. Check status any time:
         python data_sources/modules/linkedin_auth.py status

AFTER SETUP
    linkedin_publisher.py automatically calls get_managed_token() and refreshes
    as needed — no further action until the refresh token itself expires (365
    days) or, for non-entitled apps, every ~57 days.

CLI
    python data_sources/modules/linkedin_auth.py login     # interactive bootstrap
    python data_sources/modules/linkedin_auth.py refresh   # force a refresh now
    python data_sources/modules/linkedin_auth.py status    # show token health
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import secrets
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Dict, Optional

import requests


AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

DEFAULT_SCOPES = "w_organization_social r_organization_social"
DEFAULT_REDIRECT_URI = "http://localhost:8000/callback"

# Documented LinkedIn lifetimes, used as fallbacks when the API omits/garbles them.
ACCESS_TOKEN_TTL_FALLBACK = 5_184_000       # 60 days
REFRESH_TOKEN_TTL_FALLBACK = 31_536_000     # 365 days

# Renew this far ahead of expiry to absorb clock skew and pipeline scheduling gaps.
EARLY_REFRESH_SECONDS = 3 * 24 * 3600       # 3 days

# LinkedIn's own docs ship a buggy sample where refresh_token_expires_in is given
# in MINUTES (525600) under a field labelled seconds. Any refresh TTL below this
# floor is treated as that bug and replaced with the documented 365-day value.
MIN_PLAUSIBLE_REFRESH_TTL = 30 * 24 * 3600  # 30 days

MODULE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = MODULE_DIR.parent / "config"
DEFAULT_ENV_PATH = CONFIG_DIR / ".env"
DEFAULT_TOKEN_STORE = CONFIG_DIR / "linkedin_token.json"


class LinkedInAuthError(Exception):
    """Any auth-layer failure."""


class LinkedInReauthRequired(LinkedInAuthError):
    """Interactive `login` must be re-run — no way to refresh non-interactively."""


class LinkedInTokenHTTPError(LinkedInAuthError):
    """The token endpoint returned a 4xx/5xx."""

    def __init__(self, status: int, error: Optional[str], description: Optional[str], body: str):
        self.status = status
        self.error = error
        self.description = description
        self.body = body
        detail = " ".join(p for p in (error, description) if p)
        super().__init__(f"Token endpoint returned HTTP {status}: {detail or body[:200]}")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # Prefer the module-relative path so it works regardless of CWD; then also try
    # the repo-root-relative path the rest of the codebase uses.
    if DEFAULT_ENV_PATH.exists():
        load_dotenv(DEFAULT_ENV_PATH)
    load_dotenv("data_sources/config/.env")


def _redact(token: Optional[str]) -> str:
    if not token:
        return "(none)"
    if len(token) <= 12:
        return "…"
    return f"{token[:6]}…{token[-4:]} (len {len(token)})"


def _fmt_delta(seconds: Optional[float]) -> str:
    if seconds is None:
        return "unknown"
    seconds = int(seconds)
    if seconds <= 0:
        return "expired"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h {minutes}m"


class TokenStore:
    """A 0600, atomically-written JSON file holding the rotating token bundle."""

    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> Optional[Dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def save(self, data: Dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        # O_CREAT|O_TRUNC with mode 0o600 so long-lived tokens are never world-readable.
        fd = os.open(str(tmp), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(str(tmp), str(self.path))  # atomic; never leaves a half-written store
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass


class LinkedInAuth:
    def __init__(self, strict: bool = True):
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", DEFAULT_REDIRECT_URI)
        self.scopes = os.getenv("LINKEDIN_SCOPES", DEFAULT_SCOPES)
        self.store = TokenStore(os.getenv("LINKEDIN_TOKEN_STORE") or str(DEFAULT_TOKEN_STORE))
        if strict and not self.is_configured():
            raise LinkedInAuthError(
                "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in "
                "data_sources/config/.env (copy them from your app's Auth tab)."
            )

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    # ---- HTTP -------------------------------------------------------------

    def _post_token(self, data: Dict, context: str) -> Dict:
        # LinkedIn's /oauth/v2/accessToken requires form-encoding for ALL grants.
        try:
            r = requests.post(
                TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
        except requests.RequestException as e:
            raise LinkedInAuthError(f"Network error during {context}: {e}")

        if r.status_code >= 400:
            error = description = None
            try:
                body = r.json()
                error = body.get("error")
                description = body.get("error_description")
            except ValueError:
                pass
            raise LinkedInTokenHTTPError(r.status_code, error, description, r.text[:500])

        try:
            return r.json()
        except ValueError:
            raise LinkedInAuthError(f"{context}: token endpoint returned non-JSON: {r.text[:200]}")

    # ---- Persistence ------------------------------------------------------

    def _persist(self, resp: Dict, is_refresh: bool) -> Dict:
        """Merge a token response into the store, computing absolute expiries."""
        store = self.store.load() or {}
        now = time.time()

        access_token = resp.get("access_token")
        if not access_token:
            # Log only the KEYS, never the values — a malformed response could carry
            # a refresh_token or other sensitive fields we must not dump to logs.
            raise LinkedInAuthError(
                f"Token response missing access_token (response keys: {sorted(resp)})"
            )

        expires_in = int(resp.get("expires_in") or ACCESS_TOKEN_TTL_FALLBACK)
        store["access_token"] = access_token
        store["access_token_expires_at"] = now + expires_in
        store["scope"] = resp.get("scope", store.get("scope"))
        store["obtained_at"] = now

        # Refresh-token rotation: LinkedIn MAY return a new refresh_token. Overwrite
        # when present; keep the existing one when the field is absent.
        if resp.get("refresh_token"):
            store["refresh_token"] = resp["refresh_token"]

        # Refresh-token expiry: only recompute when the field is actually returned.
        # The 365-day window counts down from ORIGINAL issuance and is not extended
        # by a refresh, so we honour whatever (possibly decremented) value we get.
        rt_ttl_raw = resp.get("refresh_token_expires_in")
        if rt_ttl_raw is not None:
            rt_ttl = int(rt_ttl_raw)
            # LinkedIn's refresh TTL is documented as 365 days. Reject implausible
            # values: zero/negative (would persist an already-dead token), the known
            # minutes-as-seconds doc bug (e.g. 525600 ≈ 6 days), or absurdly large
            # garbage — in all cases fall back to the documented 365-day lifetime.
            if not (MIN_PLAUSIBLE_REFRESH_TTL <= rt_ttl <= 2 * REFRESH_TOKEN_TTL_FALLBACK):
                print(
                    f"⚠️  LinkedIn returned an implausible refresh_token_expires_in={rt_ttl}s "
                    f"(known doc/API bug). Assuming the documented 365-day lifetime.",
                    file=sys.stderr,
                )
                rt_ttl = REFRESH_TOKEN_TTL_FALLBACK
            store["refresh_token_expires_at"] = now + rt_ttl
        elif not is_refresh and store.get("refresh_token"):
            # Initial exchange returned a refresh_token but no TTL — assume 365 days.
            store.setdefault("refresh_token_expires_at", now + REFRESH_TOKEN_TTL_FALLBACK)

        self.store.save(store)
        return store

    def _purge_refresh(self, store: Dict) -> None:
        store.pop("refresh_token", None)
        store.pop("refresh_token_expires_at", None)
        self.store.save(store)

    # ---- Grants -----------------------------------------------------------

    def build_authorize_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": self.scopes,  # space-delimited; quote() encodes the space as %20
        }
        return AUTHORIZE_URL + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    def exchange_code(self, code: str) -> Dict:
        resp = self._post_token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,  # must match the authorize request
            },
            "authorization-code exchange",
        )
        bundle = self._persist(resp, is_refresh=False)
        if not bundle.get("refresh_token"):
            print(
                "\n⚠️  LinkedIn did NOT issue a refresh token for this app.\n"
                "    This app is not entitled to programmatic refresh tokens, so the\n"
                "    60-day access token cannot be renewed automatically. You'll need to\n"
                "    re-run this login roughly every ~57 days:\n"
                "        python data_sources/modules/linkedin_auth.py login\n"
                "    To enable true hands-off refresh, request 'programmatic refresh\n"
                "    tokens' for your app via LinkedIn Developer Support.\n",
                file=sys.stderr,
            )
        return bundle

    def refresh(self) -> Dict:
        store = self.store.load() or {}
        refresh_token = store.get("refresh_token")
        if not refresh_token:
            raise LinkedInReauthRequired(
                "No refresh token stored (this app may not be entitled to programmatic "
                "refresh tokens). Re-run: python data_sources/modules/linkedin_auth.py login"
            )
        try:
            resp = self._post_token(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                "refresh-token exchange",
            )
        except LinkedInTokenHTTPError as e:
            # An expired/revoked refresh token comes back as HTTP 400 (invalid_grant /
            # invalid_request). Purge it and force interactive re-login rather than
            # retrying a dead credential forever.
            if e.status == 400:
                self._purge_refresh(store)
                raise LinkedInReauthRequired(
                    f"Refresh token is invalid, expired, or revoked "
                    f"({e.error or 'HTTP 400'}). Re-run: "
                    f"python data_sources/modules/linkedin_auth.py login"
                )
            raise
        return self._persist(resp, is_refresh=True)

    # ---- Interactive login (localhost loopback) ---------------------------

    def login_interactive(self) -> Dict:
        parsed = urllib.parse.urlparse(self.redirect_uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or 80
        expected_path = parsed.path or "/"
        state = secrets.token_urlsafe(24)
        auth_url = self.build_authorize_url(state)
        captured: Dict[str, Optional[str]] = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 (http.server API)
                parts = urllib.parse.urlparse(self.path)
                if parts.path != expected_path:
                    self.send_response(404)
                    self.end_headers()
                    return
                q = urllib.parse.parse_qs(parts.query)
                captured["code"] = (q.get("code") or [None])[0]
                captured["state"] = (q.get("state") or [None])[0]
                captured["error"] = (q.get("error") or [None])[0]
                captured["error_description"] = (q.get("error_description") or [None])[0]
                ok = bool(captured.get("code"))
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                heading = "complete" if ok else "failed"
                detail = (
                    "You can close this tab and return to the terminal."
                    if ok
                    else f"Error: {captured.get('error')} — {captured.get('error_description')}"
                )
                self.wfile.write(
                    f"<html><body style='font-family:sans-serif'>"
                    f"<h2>LinkedIn authorization {heading}</h2><p>{detail}</p>"
                    f"</body></html>".encode("utf-8")
                )

            def log_message(self, *args):  # silence default stderr logging
                return

        try:
            httpd = http.server.HTTPServer((host, port), Handler)
        except OSError as e:
            raise LinkedInAuthError(
                f"Could not bind {host}:{port} for the OAuth callback ({e}). "
                f"Free the port or set LINKEDIN_REDIRECT_URI to another port and register "
                f"that exact URL in your app's Auth tab."
            )

        httpd.timeout = 300
        print("Opening your browser to authorize LinkedIn access…")
        print(f"If it doesn't open automatically, visit:\n\n    {auth_url}\n")
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass

        deadline = time.time() + 600  # 10-minute overall budget
        try:
            while "code" not in captured and "error" not in captured:
                if time.time() > deadline:
                    raise LinkedInAuthError("Timed out waiting for the LinkedIn callback (10 min).")
                httpd.handle_request()
        finally:
            httpd.server_close()

        if captured.get("error"):
            raise LinkedInAuthError(
                f"Authorization denied: {captured['error']} — {captured.get('error_description')}"
            )
        if not captured.get("code"):
            raise LinkedInAuthError("No authorization code received on the callback.")
        if captured.get("state") != state:
            raise LinkedInAuthError("OAuth state mismatch — possible CSRF. Aborting login.")

        return self.exchange_code(captured["code"])

    # ---- The function the publisher calls ---------------------------------

    def ensure_valid_token(self, interactive: bool = False) -> str:
        """Return a live access token, refreshing/re-logging in as needed.

        Never returns an expired token. Raises LinkedInReauthRequired when the
        only way forward is an interactive `login` and interactive=False.
        """
        store = self.store.load()
        if not store or not store.get("access_token"):
            if interactive:
                return self.login_interactive()["access_token"]
            raise LinkedInReauthRequired(
                "No LinkedIn token found. Run once: "
                "python data_sources/modules/linkedin_auth.py login"
            )

        now = time.time()
        access_exp = store.get("access_token_expires_at", 0)
        if now < access_exp - EARLY_REFRESH_SECONDS:
            return store["access_token"]  # comfortably valid

        # Access token is expiring (or expired) — try to renew.
        if store.get("refresh_token"):
            rt_exp = store.get("refresh_token_expires_at")
            if rt_exp is not None and now >= rt_exp - EARLY_REFRESH_SECONDS:
                if interactive:
                    return self.login_interactive()["access_token"]
                raise LinkedInReauthRequired(
                    "LinkedIn refresh token is at/near its 365-day limit. Re-run: "
                    "python data_sources/modules/linkedin_auth.py login"
                )
            try:
                return self.refresh()["access_token"]
            except LinkedInReauthRequired:
                if interactive:
                    return self.login_interactive()["access_token"]
                raise

        # No refresh token (unentitled app). Keep publishing until the HARD expiry,
        # then demand a re-login. This maximises hands-off time without ever handing
        # back a dead token.
        if now < access_exp:
            print(
                f"⚠️  LinkedIn access token expires in {_fmt_delta(access_exp - now)} and "
                f"cannot be auto-refreshed (no refresh token). Re-run "
                f"`python data_sources/modules/linkedin_auth.py login` soon.",
                file=sys.stderr,
            )
            return store["access_token"]

        if interactive:
            return self.login_interactive()["access_token"]
        raise LinkedInReauthRequired(
            "LinkedIn access token has expired and there is no refresh token. Re-run: "
            "python data_sources/modules/linkedin_auth.py login"
        )


# ---------------------------------------------------------------------------
# Module-level convenience API (used by linkedin_publisher.py)
# ---------------------------------------------------------------------------

def get_managed_token() -> Optional[str]:
    """Return a valid, auto-refreshed access token, or None if the auth helper
    isn't set up (missing client creds or no token store) — in which case the
    caller should fall back to a static LINKEDIN_ACCESS_TOKEN env var.

    Raises LinkedInReauthRequired if a token store EXISTS but is dead and cannot
    be refreshed — callers must surface this loudly rather than silently posting
    with an expired token.
    """
    _load_env()
    auth = LinkedInAuth(strict=False)
    if not auth.is_configured() or not auth.store.load():
        return None
    return auth.ensure_valid_token(interactive=False)


def ensure_valid_token(interactive: bool = False) -> str:
    _load_env()
    return LinkedInAuth(strict=True).ensure_valid_token(interactive=interactive)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_status(auth: LinkedInAuth) -> None:
    store = auth.store.load()
    print(f"Token store: {auth.store.path}")
    print(f"Configured : {'yes' if auth.is_configured() else 'NO (set LINKEDIN_CLIENT_ID/SECRET)'}")
    if not store:
        print("Status     : no token stored — run `login` once.")
        return
    now = time.time()
    access_exp = store.get("access_token_expires_at")
    print(f"Access token : {_redact(store.get('access_token'))}")
    print(f"  scope      : {store.get('scope')}")
    if access_exp:
        print(f"  expires in : {_fmt_delta(access_exp - now)} "
              f"({'valid' if now < access_exp else 'EXPIRED'})")
    if store.get("refresh_token"):
        rt_exp = store.get("refresh_token_expires_at")
        print(f"Refresh token: {_redact(store.get('refresh_token'))}")
        print(f"  expires in : {_fmt_delta((rt_exp - now) if rt_exp else None)}")
        print("  auto-refresh: ENABLED")
    else:
        print("Refresh token: NONE — app not entitled to programmatic refresh tokens.")
        print("  auto-refresh: DISABLED (manual `login` required ~every 57 days)")


def _main() -> int:
    _load_env()
    parser = argparse.ArgumentParser(
        description="LinkedIn OAuth: one-time login + automatic token refresh."
    )
    parser.add_argument(
        "command",
        choices=["login", "refresh", "status"],
        help="login: interactive bootstrap · refresh: force a refresh · status: show token health",
    )
    args = parser.parse_args()

    try:
        if args.command == "status":
            _print_status(LinkedInAuth(strict=False))
            return 0

        auth = LinkedInAuth(strict=True)
        if args.command == "login":
            bundle = auth.login_interactive()
            print("\n✅ Login complete.")
            _print_status(auth)
            return 0
        if args.command == "refresh":
            auth.refresh()
            print("✅ Refreshed.")
            _print_status(auth)
            return 0
    except LinkedInReauthRequired as e:
        print(f"\n🔑 Re-login required: {e}", file=sys.stderr)
        return 2
    except LinkedInAuthError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(_main())
