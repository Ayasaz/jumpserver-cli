"""
SSH connect command for JumpServer CLI.

Establishes an interactive SSH session to an authorized asset through the
JumpServer KoKo gateway, using a short-lived connection token.

Flow:
  1. Resolve the asset by name or id via ``perms/users/self/assets/``.
  2. Pick an authorized account (``--account`` or the only one available).
  3. Create a connection token (``authentication/connection-token/``).
  4. Hand the terminal over to ``ssh`` against the KoKo gateway, logging in
     as ``JMS-<token_id>`` with the token value as the password.

The login convention follows JumpServer's "SSH client + connection token"
method: username ``JMS-<ConnectionToken.id>`` / password ``ConnectionToken.value``.
"""
import os
import shutil
import sys
from urllib.parse import urlparse

import click

from cli_anything.jumpserver.core.session import Session
from cli_anything.jumpserver.utils import require_auth, CLIError


# Default KoKo SSH gateway port (JumpServer default).
DEFAULT_KOKO_SSH_PORT = 2222


def _resolve_asset(client, target: str) -> dict:
    """Resolve a target (name or id) to a single authorized asset."""
    assets = client.my_assets(search=target)
    # Exact id match wins.
    for a in assets:
        if a.get("id") == target:
            return a
    # Exact name match next.
    exact = [a for a in assets if a.get("name") == target]
    if len(exact) == 1:
        return exact[0]
    if not assets:
        raise CLIError(
            f"No authorized asset matches '{target}'.",
            "Check 'jumpserver user my-assets' for the assets you can access.",
        )
    if len(assets) == 1:
        return assets[0]
    names = ", ".join(f"{a.get('name')} ({a.get('address')})" for a in assets[:10])
    raise CLIError(
        f"'{target}' matches multiple assets, please be more specific.",
        f"Candidates: {names}",
    )


def _pick_account(asset: dict, account: str | None) -> dict:
    """Choose an authorized account on the asset."""
    accounts = asset.get("permed_accounts", []) or []
    if not accounts:
        raise CLIError(
            f"No authorized account on asset '{asset.get('name')}'.",
            "Ask an administrator to grant an account for this asset.",
        )
    if account:
        for ac in accounts:
            if account in (ac.get("alias"), ac.get("username"), ac.get("name")):
                return ac
        avail = ", ".join(
            f"{ac.get('alias')} (user={ac.get('username')})" for ac in accounts
        )
        raise CLIError(
            f"Account '{account}' not found on '{asset.get('name')}'.",
            f"Available: {avail}",
        )
    if len(accounts) == 1:
        return accounts[0]
    avail = ", ".join(
        f"{ac.get('alias')} (user={ac.get('username')})" for ac in accounts
    )
    raise CLIError(
        f"Asset '{asset.get('name')}' has multiple accounts; choose one with --account.",
        f"Available: {avail}",
    )


def _gateway_host(session: Session, override: str | None) -> str:
    """Determine the KoKo SSH gateway host."""
    if override:
        return override
    host = urlparse(session.base_url).hostname
    if not host:
        raise CLIError("Cannot determine gateway host from session base_url.")
    return host


@click.command(name="connect")
@click.argument("target")
@click.option("--account", "-a", default=None,
              help="Account alias or username to log in with (default: the only one)")
@click.option("--port", "-p", default=None, type=int,
              help=f"KoKo SSH gateway port (default: {DEFAULT_KOKO_SSH_PORT} or $JUMPSERVER_SSH_PORT)")
@click.option("--ssh-host", "ssh_host", default=None,
              help="Override the SSH gateway host (default: host of the API URL)")
@click.option("--protocol", default="ssh", help="Connection protocol (default: ssh)")
@click.option("--no-strict-host-key", is_flag=True, default=False,
              help="Pass StrictHostKeyChecking=no to ssh")
@click.option("--print-command", "print_only", is_flag=True, default=False,
              help="Print the ssh command (password masked) without connecting")
def connect_command(target, account, port, ssh_host, protocol,
                    no_strict_host_key, print_only):
    """Open an interactive SSH session to an authorized asset (TARGET = name or id).

    \b
    Examples:
      jumpserver connect warehouse-test
      jumpserver connect warehouse-test --account dev研发
      jumpserver connect 2697510e-71f9-4474-b619-8edeb082668c -p 2222
    """
    session = Session.load()
    client = require_auth(session)

    asset = _resolve_asset(client, target)
    # The search endpoint omits permed_accounts; fetch full detail.
    detail = client.get_my_asset(asset["id"])
    chosen = _pick_account(detail, account)

    token = client.create_connection_token(
        asset_id=detail["id"],
        account=chosen.get("alias") or chosen.get("username"),
        protocol=protocol,
        connect_method="ssh",
    )

    token_id = token["id"]
    token_value = token.get("value", "")
    ssh_user = f"JMS-{token_id}"
    host = _gateway_host(session, ssh_host)
    ssh_port = port or int(os.environ.get("JUMPSERVER_SSH_PORT", DEFAULT_KOKO_SSH_PORT))

    ssh_args = ["ssh", "-tt", "-p", str(ssh_port)]
    if no_strict_host_key:
        ssh_args += ["-o", "StrictHostKeyChecking=no"]
    ssh_args.append(f"{ssh_user}@{host}")

    asset_disp = f"{detail.get('name')} ({detail.get('address')})"
    acct_disp = chosen.get("alias") or chosen.get("username")

    if print_only:
        masked = " ".join(ssh_args)
        click.echo(click.style(f"# asset:   {asset_disp}", fg="cyan"))
        click.echo(click.style(f"# account: {acct_disp}", fg="cyan"))
        click.echo(click.style(f"# token expires in {token.get('expire_time')}s", fg="cyan"))
        click.echo(masked)
        click.echo(click.style(
            "# password: the token value (hidden). Run 'connect' without "
            "--print-command to log in automatically.", fg="yellow"))
        return

    click.echo(click.style(
        f"Connecting to {asset_disp} as {acct_disp} via {host}:{ssh_port} ...",
        fg="green",
    ))

    sshpass = shutil.which("sshpass")
    if sshpass:
        # Automated password handoff; secret never appears in argv visibly
        # to other users because it's passed via env (-e).
        env = dict(os.environ, SSHPASS=token_value)
        os.execvpe("sshpass", ["sshpass", "-e", *ssh_args], env)
    else:
        click.echo(click.style(
            "sshpass not found; at the password prompt, paste this token value:",
            fg="yellow",
        ))
        click.echo(click.style(token_value, fg="yellow", bold=True))
        click.echo(click.style(
            "(tip: install sshpass for automatic password handoff)", fg="bright_black",
        ))
        try:
            os.execvp("ssh", ssh_args)
        except FileNotFoundError:
            raise CLIError("ssh client not found on PATH.")
