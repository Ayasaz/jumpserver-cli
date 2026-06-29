"""
Session management for JumpServer CLI.

Manages API connection state, authentication tokens, and session persistence.
"""
import html
import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


SESSION_FILE = Path.home() / ".jumpserver-cli" / "session.json"


@dataclass
class Session:
    """JumpServer API session state."""

    base_url: str = ""
    username: str = ""
    token: str = ""
    token_expiry: float = 0.0
    refresh_token: str = ""
    org_id: str = ""
    org_name: str = ""
    verify_ssl: bool = True
    timeout: int = 30
    # Django web-session cookies (sessionid/csrftoken), needed by the Koko web
    # terminal which does not honour the Bearer API token.
    web_cookies: dict[str, str] = field(default_factory=dict)
    _current_user: dict[str, Any] | None = field(default=None, repr=False)

    def save(self) -> None:
        """Persist session to disk."""
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        data.pop("_current_user", None)
        SESSION_FILE.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> "Session":
        """Load session from disk, returns empty session if not found."""
        if SESSION_FILE.exists():
            try:
                data = json.loads(SESSION_FILE.read_text())
                data.pop("_current_user", None)
                return cls(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def clear(self) -> None:
        """Remove persisted session."""
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    def is_authenticated(self) -> bool:
        """Check if the session has a valid token."""
        if not self.token:
            return False
        if self.token_expiry and time.time() > self.token_expiry:
            return False
        return True

    def get_client(self) -> "JumpServerClient":
        """Get an API client configured with this session."""
        return JumpServerClient(self)


class JumpServerClient:
    """HTTP client for JumpServer REST API with retry support."""

    def __init__(self, session: Session):
        self.session = session
        self._http = requests.Session()
        self._http.verify = session.verify_ssl
        self._http.timeout = session.timeout

        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._http.mount("http://", adapter)
        self._http.mount("https://", adapter)

        # Restore any persisted Django web-session cookies for the Koko terminal.
        host = urlparse(session.base_url).hostname or ""
        for name, value in (session.web_cookies or {}).items():
            self._http.cookies.set(name, value, domain=host)

    @property
    def headers(self) -> dict[str, str]:
        h = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.session.token:
            h["Authorization"] = f"Bearer {self.session.token}"
        if self.session.org_id:
            h["X-JMS-ORG"] = self.session.org_id
        return h

    def _url(self, path: str) -> str:
        base = self.session.base_url.rstrip("/")
        return f"{base}/api/v1/{path.lstrip('/')}"

    def request(
        self, method: str, path: str, **kwargs
    ) -> requests.Response:
        url = self._url(path)
        kwargs.setdefault("headers", self.headers)
        return self._http.request(method, url, **kwargs)

    def get(self, path: str, params: dict | None = None) -> requests.Response:
        return self.request("GET", path, params=params)

    def post(
        self, path: str, data: dict | None = None
    ) -> requests.Response:
        return self.request("POST", path, json=data)

    def put(
        self, path: str, data: dict | None = None
    ) -> requests.Response:
        return self.request("PUT", path, json=data)

    def patch(
        self, path: str, data: dict | None = None
    ) -> requests.Response:
        return self.request("PATCH", path, json=data)

    def delete(self, path: str) -> requests.Response:
        return self.request("DELETE", path)

    def login(
        self, username: str, password: str
    ) -> dict[str, Any]:
        """Authenticate and store token."""
        resp = self.post(
            "authentication/auth/",
            data={"username": username, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self.session.token = data.get("token", "")
        self.session.username = username
        self.session.token_expiry = time.time() + 3600  # default 1h
        self.session.save()
        return data

    def web_login(self, username: str, password: str) -> bool:
        """Establish a Django web session (cookies) in addition to the API token.

        The Koko web terminal (used by ``ops run --transport koko``) authenticates
        by session cookie, not the Bearer API token, so we perform a form login
        against ``/core/auth/login/`` and persist the resulting cookies. Best
        effort: returns False instead of raising if the web login is unavailable.
        """
        base = self.session.base_url.rstrip("/")
        login_url = f"{base}/core/auth/login/"
        try:
            page = self._http.get(
                login_url, timeout=self.session.timeout,
                headers={"Accept": "text/html"},
            )
            if page.status_code >= 400:
                return False
            csrf = self._http.cookies.get("csrftoken")
            m = re.search(
                r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)',
                page.text,
            )
            if m:
                csrf = html.unescape(m.group(1))
            if not csrf:
                return False

            post = self._http.post(
                login_url,
                data={
                    "username": username,
                    "password": password,
                    "csrfmiddlewaretoken": csrf,
                    "next": "/",
                },
                headers={
                    "Referer": login_url,
                    "X-CSRFToken": csrf,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                allow_redirects=False,
                timeout=self.session.timeout,
            )
            if post.status_code not in (302, 303):
                return False
            location = post.headers.get("Location") or ""
            if "/core/auth/login/guard/" in location:
                self._http.get(
                    location if location.startswith("http") else f"{base}{location}",
                    headers={"Referer": login_url},
                    allow_redirects=False,
                    timeout=self.session.timeout,
                )
        except requests.RequestException:
            return False

        cookies = {c.name: c.value for c in self._http.cookies}
        if "sessionid" not in cookies and not any("sessionid" in k.lower() for k in cookies):
            return False
        self.session.web_cookies = cookies
        self.session.save()
        return True

    def logout(self) -> None:
        """Invalidate the session."""
        self.session.clear()

    def get_current_user(self) -> dict[str, Any]:
        """Get current authenticated user profile."""
        resp = self.get("users/profile/")
        resp.raise_for_status()
        return resp.json()

    def my_assets(self, search: str | None = None) -> list[dict[str, Any]]:
        """List assets the current user is authorized to access."""
        params = {"search": search} if search else None
        resp = self.get("perms/users/self/assets/", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", data) if isinstance(data, dict) else data

    def get_my_asset(self, asset_id: str) -> dict[str, Any]:
        """Get details (incl. permed_accounts/protocols) of one authorized asset."""
        resp = self.get(f"perms/users/self/assets/{asset_id}/")
        resp.raise_for_status()
        return resp.json()

    def create_connection_token(
        self,
        asset_id: str,
        account: str,
        protocol: str = "ssh",
        connect_method: str = "ssh",
        input_username: str = "",
    ) -> dict[str, Any]:
        """Create a connection token used to log in to an asset via the gateway."""
        body = {
            "asset": asset_id,
            "account": account,
            "protocol": protocol,
            "connect_method": connect_method,
        }
        if input_username:
            body["input_username"] = input_username
        resp = self.post("authentication/connection-token/", data=body)
        resp.raise_for_status()
        return resp.json()

    def paginate(
        self, path: str, params: dict | None = None, limit: int = 100
    ):
        """Generator that yields results across all pages."""
        params = (params or {}).copy()
        params.setdefault("limit", limit)
        params.setdefault("offset", 0)

        while True:
            resp = self.get(path, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", data if isinstance(data, list) else [])
            if not results:
                break
            yield from results
            if len(results) < limit:
                break
            params["offset"] += len(results)
