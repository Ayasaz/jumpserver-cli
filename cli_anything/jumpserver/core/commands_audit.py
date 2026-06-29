"""
Audit and operations commands for JumpServer CLI.

Manages audit logs, login logs, operate logs, and job execution.
"""
import base64 as _base64
import json as _json
import re
import ssl as _ssl
import time
from urllib.parse import urlencode, urlparse, urlunparse

import click

from cli_anything.jumpserver.core.session import Session
from cli_anything.jumpserver.utils import (
    require_auth,
    handle_api_error,
    print_result,
    CLIError,
)
from cli_anything.jumpserver.core.commands_connect import (
    _resolve_asset,
    _pick_account,
)

# Sentinel markers used to delimit base64-encoded command output, so that
# multi-line / binary / locale-mangled output survives the Ansible "raw"
# transport and ANSI cleanup intact.
_B64_START = "__JS_B64_START__"
_B64_END = "__JS_B64_END__"

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
# OSC (Operating System Command) sequences, e.g. window-title updates.
_OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

# Sentinel appended after the user command in a Koko web-terminal session so we
# can detect completion and capture the exit code from the streamed PTY output.
_KOKO_DONE = "__JS_KOKO_DONE__"


@click.group(name="audit")
def audit_group():
    """View audit logs and reports."""
    pass


# ─── Login Logs ──────────────────────────────────────────────


@audit_group.command(name="login")
@click.option("--search", "-s", default=None, help="Search by username")
@click.option("--status", default=None, type=click.Choice(["success", "failed"]), help="Login status")
@click.option("--limit", default=20, help="Results per page")
@click.option("--offset", default=0, help="Pagination offset")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
def login_logs(search, status, limit, offset, output):
    """View user login audit logs."""
    sess = Session.load()
    client = require_auth(sess)

    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    if status:
        params["status"] = "1" if status == "success" else "0"

    resp = client.get("audits/login-logs/", params=params)
    handle_api_error(resp, "get login logs")
    print_result(resp.json(), fmt=output)


# ─── Operate Logs ────────────────────────────────────────────


@audit_group.command(name="operate")
@click.option("--search", "-s", default=None, help="Search by user or resource")
@click.option("--user", "-u", default=None, help="Filter by user ID")
@click.option("--action", "-a", default=None, type=click.Choice(["create", "update", "delete"]), help="Action type")
@click.option("--resource", "-r", default=None, help="Resource type (e.g., Asset, User)")
@click.option("--limit", default=20, help="Results per page")
@click.option("--offset", default=0, help="Pagination offset")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
@click.option("--columns", "-c", default="user,action,resource_type,resource,datetime", help="Comma-separated column names")
def operate_logs(search, user, action, resource, limit, offset, output, columns):
    """View resource operation audit logs."""
    sess = Session.load()
    client = require_auth(sess)

    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    if user:
        params["user"] = user
    if action:
        params["action"] = action
    if resource:
        params["resource_type"] = resource

    resp = client.get("audits/operate-logs/", params=params)
    handle_api_error(resp, "get operate logs")
    print_result(resp.json(), fmt=output, columns=columns)


# ─── FTP Logs ────────────────────────────────────────────────


@audit_group.command(name="ftp")
@click.option("--search", "-s", default=None, help="Search by user or filename")
@click.option("--user", "-u", default=None, help="Filter by user ID")
@click.option("--limit", default=20, help="Results per page")
@click.option("--offset", default=0, help="Pagination offset")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
def ftp_logs(search, user, limit, offset, output):
    """View FTP file transfer audit logs."""
    sess = Session.load()
    client = require_auth(sess)

    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    if user:
        params["user"] = user

    resp = client.get("audits/ftp-logs/", params=params)
    handle_api_error(resp, "get FTP logs")
    print_result(resp.json(), fmt=output)


# ─── Password Change Logs ─────────────────────────────────────


@audit_group.command(name="password")
@click.option("--search", "-s", default=None, help="Search by user")
@click.option("--limit", default=20, help="Results per page")
@click.option("--offset", default=0, help="Pagination offset")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
def password_logs(search, limit, offset, output):
    """View password change audit logs."""
    sess = Session.load()
    client = require_auth(sess)

    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search

    resp = client.get("audits/password-change-logs/", params=params)
    handle_api_error(resp, "get password change logs")
    print_result(resp.json(), fmt=output)


# ─── Activity Logs ────────────────────────────────────────────


@audit_group.command(name="activity")
@click.option("--limit", default=20, help="Results per page")
@click.option("--offset", default=0, help="Pagination offset")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
def activity_logs(limit, offset, output):
    """View user activity logs."""
    sess = Session.load()
    client = require_auth(sess)

    params = {"limit": limit, "offset": offset}
    resp = client.get("audits/activities/", params=params)
    handle_api_error(resp, "get activity logs")
    print_result(resp.json(), fmt=output)


# ─── Ops / Job Management ────────────────────────────────────


@click.group(name="ops")
def ops_group():
    """Manage operations and job execution."""
    pass


@ops_group.command(name="job-list")
@click.option("--search", "-s", default=None, help="Search by name")
@click.option("--limit", default=20, help="Results per page")
@click.option("--offset", default=0, help="Pagination offset")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
def job_list(search, limit, offset, output):
    """List execution jobs."""
    sess = Session.load()
    client = require_auth(sess)

    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search

    resp = client.get("ops/jobs/", params=params)
    handle_api_error(resp, "list jobs")
    print_result(resp.json(), fmt=output)


@ops_group.command(name="job-log")
@click.argument("execution_id")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
def job_log(execution_id, output):
    """Get job execution log."""
    sess = Session.load()
    client = require_auth(sess)
    resp = client.get(f"ops/job-executions/{execution_id}/")
    handle_api_error(resp, "get job execution")
    print_result(resp.json(), fmt=output)


@ops_group.command(name="adhoc-list")
@click.option("--search", "-s", default=None, help="Search by name")
@click.option("--limit", default=20, help="Results per page")
@click.option("--offset", default=0, help="Pagination offset")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
def adhoc_list(search, limit, offset, output):
    """List ad-hoc command executions."""
    sess = Session.load()
    client = require_auth(sess)

    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search

    resp = client.get("ops/adhocs/", params=params)
    handle_api_error(resp, "list adhoc executions")
    print_result(resp.json(), fmt=output)


@ops_group.command(name="playbook-list")
@click.option("--search", "-s", default=None, help="Search by name")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
def playbook_list(search, output):
    """List Ansible playbooks."""
    sess = Session.load()
    client = require_auth(sess)

    params = {}
    if search:
        params["search"] = search

    resp = client.get("ops/playbooks/", params=params)
    handle_api_error(resp, "list playbooks")
    print_result(resp.json(), fmt=output)


# ─── Ad-hoc command execution (non-interactive SSH over the ops API) ──────


def _clean_output(text: str) -> str:
    """Strip ANSI escapes / CR / NULs from an execution log."""
    text = _ANSI_RE.sub("", text)
    return text.replace("\r\n", "\n").replace("\r", "").replace("\x00", "")


def _wrap_base64(cmd: str) -> str:
    """Wrap a command so its combined stdout/stderr is emitted base64-encoded
    between sentinel markers (robust against ANSI/locale/multiline noise)."""
    return (
        f"echo {_B64_START}; {{ {cmd} ; }} 2>&1 | base64 | tr -d '\\n'; "
        f"echo; echo {_B64_END}"
    )


def _decode_base64(text: str) -> str:
    """Extract and decode the base64 blob delimited by the sentinels."""
    if _B64_START not in text or _B64_END not in text:
        return text
    blob = text.split(_B64_START, 1)[1].split(_B64_END, 1)[0]
    blob = "".join(blob.split())
    try:
        return _base64.b64decode(blob).decode("utf-8", "replace")
    except Exception as exc:  # pragma: no cover - defensive
        return f"[base64 decode error: {exc}]\n{blob[:500]}"


def _fetch_execution_log(client, execution_id: str) -> str:
    """Pull the full execution log, following the incremental ``mark`` cursor."""
    full, mark = "", ""
    for _ in range(60):
        resp = client.get(
            f"ops/ansible/job-execution/{execution_id}/log/",
            params={"mark": mark},
        )
        if resp.status_code >= 400:
            break
        data = resp.json()
        if not isinstance(data, dict):
            break
        full += data.get("data", "")
        new_mark = data.get("mark", "")
        if data.get("end") or new_mark == mark:
            break
        mark = new_mark
        time.sleep(0.3)
    return full


def _koko_clean(text: str) -> str:
    """Strip ANSI/OSC escapes and CRs from a raw PTY stream."""
    text = _OSC_RE.sub("", text)
    text = _ANSI_RE.sub("", text)
    return text.replace("\r\n", "\n").replace("\r", "").replace("\x00", "")


def _koko_exit_code(text: str):
    """Return the exit code printed after the sentinel, or None if not yet seen."""
    m = re.search(rf"{re.escape(_KOKO_DONE)}:(-?\d+)", text)
    return int(m.group(1)) if m else None


def _run_via_koko(client, base_url, asset_id, account, command, timeout):
    """Run *command* on an asset through the Koko Web Terminal (websocket).

    This bypasses the Ops ad-hoc job engine (Celery/ansible), which is unreliable
    in some deployments, and drives a real PTY session via a connection token —
    the same path the interactive web terminal uses. Returns a dict with
    ``output``, ``is_success`` and ``exit_code``.
    """
    try:
        import websocket  # from the websocket-client package
    except ImportError:
        raise CLIError(
            "Koko transport requires the 'websocket-client' package.",
            "Install it with: pip install websocket-client  (or use --transport ops)",
        )

    token = client.create_connection_token(
        asset_id=asset_id,
        account=account,
        protocol="ssh",
        connect_method="web_cli",
    )
    token_id = str(token.get("id") or "").strip()
    if not token_id:
        raise CLIError(f"Connection token has no id: {str(token)[:200]}")

    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # Warm up the connect page so Koko registers the token (and sets any cookies).
    try:
        client._http.get(
            f"{origin}/koko/connect/",
            params={"token": token_id},
            headers={**client.headers, "Accept": "text/html,*/*;q=0.8"},
            allow_redirects=False,
            timeout=client.session.timeout,
        )
    except Exception:
        pass  # best-effort; the token in the ws query string is the real auth

    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = urlunparse(
        (ws_scheme, parsed.netloc, "/koko/ws/terminal/", "",
         urlencode({"token": token_id}), "")
    )
    cookie_header = "; ".join(
        f"{c.name}={c.value}" for c in client._http.cookies
    )
    header = [
        f"Origin: {origin}",
        f"Referer: {origin}/koko/connect?token={token_id}",
    ]
    if cookie_header:
        header.append(f"Cookie: {cookie_header}")
    if client.session.token:
        header.append(f"Authorization: Bearer {client.session.token}")

    sslopt = None if client.session.verify_ssl else {"cert_reqs": _ssl.CERT_NONE}
    ws = websocket.create_connection(
        ws_url, timeout=timeout, subprotocols=["JMS-KOKO"],
        header=header, sslopt=sslopt,
        # Connect to the gateway directly; a local HTTP(S) proxy (common in dev
        # environments, also read from the macOS system config) breaks the
        # websocket-client proxy path with a misleading "url is invalid".
        http_no_proxy=[parsed.hostname, "*"],
    )
    try:
        terminal_id = None
        sent = False
        parts: list[str] = []
        deadline = time.monotonic() + timeout
        wrapped = f"{command}\nprintf '\\n{_KOKO_DONE}:%s\\n' $?\n"

        def _send():
            nonlocal sent
            if terminal_id and not sent:
                time.sleep(0.5)
                ws.send(_json.dumps({
                    "id": terminal_id, "type": "TERMINAL_DATA", "data": wrapped,
                }))
                sent = True

        while time.monotonic() < deadline:
            frame = ws.recv()
            if isinstance(frame, (bytes, bytearray)):
                parts.append(frame.decode("utf-8", "replace"))
                _send()
                clean = _koko_clean("".join(parts))
                code = _koko_exit_code(clean)
                if code is not None:
                    output = re.sub(
                        rf"(?m)^.*{re.escape(_KOKO_DONE)}:-?\d+\s*$", "", clean
                    )
                    # Drop the echoed command line (first occurrence) and PTY noise:
                    # SSH MOTD banners, "Last login:" lines, and the raw shell prompt.
                    output = output.replace(command, "", 1)
                    output = re.sub(
                        r"(?m)^(?:复用SSH连接|Last login:.+).*$\n?", "", output,
                    )
                    output = re.sub(
                        r"(?m)^\[.+\]\$.*$", "", output,
                    )
                    return {
                        "output": output.strip(),
                        "is_success": code == 0,
                        "exit_code": code,
                    }
                continue

            msg = _json.loads(frame)
            mtype = msg.get("type")
            if mtype == "CONNECT":
                terminal_id = msg["id"]
                ws.send(_json.dumps({
                    "id": terminal_id, "type": "TERMINAL_INIT",
                    "data": _json.dumps({"cols": 200, "rows": 40, "code": ""}),
                }))
            elif mtype == "TERMINAL_SESSION" and terminal_id and not sent:
                _send()
            elif mtype in ("ERROR", "TERMINAL_ERROR"):
                raise CLIError(
                    f"Koko websocket error: {msg.get('err') or msg.get('data')}"
                )
            elif mtype == "CLOSE":
                break

        raise CLIError(
            f"Koko session timed out after {timeout}s without a completion marker.",
            "Raise --timeout, or retry with --transport ops.",
        )
    finally:
        try:
            ws.close()
        except Exception:
            pass


@ops_group.command(name="run")
@click.argument("target")
@click.argument("command")
@click.option("--account", "-a", default=None,
              help="Account alias or username to run as (default: the only authorized one)")
@click.option("--transport", type=click.Choice(["koko", "ops"]), default="koko",
              help="Execution path: 'koko' web terminal (default, works when the Ops "
                   "job engine is down) or 'ops' ad-hoc job.")
@click.option("--module", "-m", default="raw",
              help="Ansible module to use for --transport ops (default: raw; e.g. shell, command)")
@click.option("--timeout", "-t", "wait_timeout", default=120, type=int,
              help="Seconds to wait for the command to finish (default: 120)")
@click.option("--base64", "use_base64", is_flag=True, default=False,
              help="Encode output as base64 in transit (--transport ops only; robust for "
                   "multiline/binary/locale-mangled output)")
@click.option("--dry-run", is_flag=True, default=False,
              help="Print what would be submitted without executing")
@click.option("--output", "-o", type=click.Choice(["text", "json", "yaml"]), default="text",
              help="Output format (default: text = just the command output)")
def ops_run(target, command, account, transport, module, wait_timeout, use_base64, dry_run, output):
    """Run a shell COMMAND on an authorized asset (TARGET = name or id), non-interactively.

    A scriptable alternative to the interactive ``connect`` session. Two transports:

    \b
      koko (default) — drives the Koko Web Terminal over a websocket. Use this when
                       the Ops job engine (Celery/ansible) is down: jobs there hang
                       forever with a null task_id. Needs 'websocket-client'.
      ops            — submits a one-off ad-hoc job through the Ops API.

    \b
    Examples:
      jumpserver ops run warehouse-test "ls -lh /home/dev/logs"
      jumpserver ops run warehouse-test "grep -c ERROR app.log" --account dev研发
      jumpserver ops run warehouse-test "cat /etc/os-release" --transport ops -o json
    """
    session = Session.load()
    client = require_auth(session)

    asset = _resolve_asset(client, target)
    detail = client.get_my_asset(asset["id"])
    chosen = _pick_account(detail, account)

    if transport == "koko":
        # The web terminal authenticates by account alias/name, not username.
        runas = chosen.get("alias") or chosen.get("name") or chosen.get("username")
        if dry_run:
            print_result(
                {"transport": "koko", "asset": detail.get("name"),
                 "address": detail.get("address"), "account": runas, "command": command},
                fmt="json" if output == "text" else output,
            )
            return

        result = _run_via_koko(
            client, session.base_url, detail["id"], runas, command, wait_timeout,
        )
        text = result["output"]
        is_success = result["is_success"]

        if output in ("json", "yaml"):
            print_result(
                {
                    "transport": "koko",
                    "asset": detail.get("name"),
                    "address": detail.get("address"),
                    "runas": runas,
                    "is_success": is_success,
                    "exit_code": result["exit_code"],
                    "output": text,
                },
                fmt=output,
            )
            return

        status = click.style("OK" if is_success else "FAILED",
                             fg="green" if is_success else "red")
        header = click.style(
            f"# {detail.get('name')} ({detail.get('address')}) as {runas} ", fg="cyan",
        )
        click.echo(f"{header}[{status}]")
        click.echo(text)
        if not is_success:
            raise SystemExit(1)
        return

    runas = chosen.get("username") or chosen.get("alias")

    args = _wrap_base64(command) if use_base64 else command
    payload = {
        "name": f"adhoc-cli-{int(time.time())}",
        "module": module,
        "args": args,
        "assets": [detail["id"]],
        "runas": runas,
        "type": "adhoc",
        "instant": True,
        "is_periodic": False,
        "crontab": "",
        "interval": None,
    }

    if dry_run:
        print_result(payload, fmt="json" if output == "text" else output)
        return

    resp = client.post("ops/jobs/", data=payload)
    handle_api_error(resp, "create ad-hoc job")
    job = resp.json()
    execution_id = job.get("task_id") or job.get("id")
    if not execution_id:
        raise CLIError(
            "Ad-hoc job created but no execution id was returned.",
            f"Response: {str(job)[:300]}",
        )

    # Poll for completion.
    execution = None
    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        time.sleep(2)
        poll = client.get(f"ops/job-executions/{execution_id}/")
        if poll.status_code >= 400:
            continue
        execution = poll.json()
        if isinstance(execution, dict) and execution.get("is_finished"):
            break
    else:
        raise CLIError(
            f"Job did not finish within {wait_timeout}s (execution {execution_id}).",
            "Increase --timeout, or inspect with 'ops job-log <execution_id>'.",
        )

    raw_log = _fetch_execution_log(client, execution_id)
    text = _clean_output(raw_log)
    if use_base64:
        text = _decode_base64(text)

    is_success = bool(execution.get("is_success")) if execution else False

    if output in ("json", "yaml"):
        print_result(
            {
                "execution_id": execution_id,
                "asset": detail.get("name"),
                "address": detail.get("address"),
                "runas": runas,
                "is_success": is_success,
                "time_cost": execution.get("time_cost") if execution else None,
                "output": text.strip(),
            },
            fmt=output,
        )
        return

    # Default text mode: a short status header + the command output.
    status = click.style("OK" if is_success else "FAILED",
                         fg="green" if is_success else "red")
    header = click.style(
        f"# {detail.get('name')} ({detail.get('address')}) as {runas} ",
        fg="cyan",
    )
    click.echo(f"{header}[{status}]")
    click.echo(text.strip())
    if not is_success:
        raise SystemExit(1)
