#!/usr/bin/env python3
"""Manage a private catalog of SSH shortcuts and render ~/.ssh/config entries."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


BEGIN = "# BEGIN ssh-shortcuts managed"
END = "# END ssh-shortcuts managed"
DEFAULT_CONFIG = Path("~/.config/ssh-shortcuts/shortcuts.json").expanduser()
DEFAULT_SSH_CONFIG = Path("~/.ssh/config").expanduser()
DEFAULT_IDENTITY = "~/.ssh/id_ed25519"
VALID_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def config_path() -> Path:
    return Path(os.environ.get("SSH_SHORTCUTS_CONFIG", str(DEFAULT_CONFIG))).expanduser()


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "shortcuts": {}}
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    data.setdefault("version", 1)
    data.setdefault("shortcuts", {})
    if not isinstance(data["shortcuts"], dict):
        raise SystemExit(f"{path}: shortcuts must be an object")
    return data


def save_catalog(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def require_name(name: str) -> None:
    if not VALID_NAME.match(name):
        raise SystemExit("shortcut names may contain only letters, digits, dot, underscore, and hyphen")


def normalize_shortcut(raw: dict[str, Any]) -> dict[str, Any]:
    item = dict(raw)
    if "hostname" in item and "host" not in item:
        item["host"] = item.pop("hostname")
    if "host" not in item or not item["host"]:
        raise SystemExit("shortcut is missing required field: host")
    if "port" in item and item["port"] not in ("", None):
        item["port"] = int(item["port"])
    return item


def quote_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts if part not in ("", None))


def target_for(host: str, user: str | None) -> str:
    return f"{user}@{host}" if user else host


def direct_ssh_base(args: argparse.Namespace, *, batch: bool = False) -> list[str]:
    cmd = ["ssh"]
    if batch:
        cmd.extend(["-o", "BatchMode=yes"])
    if getattr(args, "proxy_jump", None):
        cmd.extend(["-J", args.proxy_jump])
    if getattr(args, "identity_file", None):
        cmd.extend(["-i", args.identity_file])
    if getattr(args, "port", None):
        cmd.extend(["-p", str(args.port)])
    return cmd


def ssh_command(name: str, shortcut: dict[str, Any]) -> str:
    cmd = ["ssh"]
    if shortcut.get("proxy_jump"):
        cmd.extend(["-J", shortcut["proxy_jump"]])
    if shortcut.get("identity_file"):
        cmd.extend(["-i", shortcut["identity_file"]])
    if shortcut.get("port"):
        cmd.extend(["-p", str(shortcut["port"])])
    target = shortcut.get("host", name)
    if shortcut.get("user"):
        target = f"{shortcut['user']}@{target}"
    cmd.append(target)
    return quote_command(cmd)


def render_host_block(name: str, shortcut: dict[str, Any]) -> str:
    shortcut = normalize_shortcut(shortcut)
    lines = [f"Host {name}", f"    HostName {shortcut['host']}"]
    if shortcut.get("user"):
        lines.append(f"    User {shortcut['user']}")
    if shortcut.get("port"):
        lines.append(f"    Port {shortcut['port']}")
    if shortcut.get("identity_file"):
        lines.append(f"    IdentityFile {shortcut['identity_file']}")
        lines.append("    IdentitiesOnly yes")
    if shortcut.get("proxy_jump"):
        lines.append(f"    ProxyJump {shortcut['proxy_jump']}")
    for key, value in sorted((shortcut.get("ssh_options") or {}).items()):
        lines.append(f"    {key} {value}")
    return "\n".join(lines)


def render_config(catalog: dict[str, Any]) -> str:
    blocks = []
    for name in sorted(catalog["shortcuts"]):
        require_name(name)
        blocks.append(render_host_block(name, catalog["shortcuts"][name]))
    body = "\n\n".join(blocks)
    return f"{BEGIN}\n{body}\n{END}\n" if body else f"{BEGIN}\n{END}\n"


def replace_managed_block(existing: str, managed: str) -> str:
    pattern = re.compile(rf"{re.escape(BEGIN)}.*?{re.escape(END)}\n?", re.S)
    if pattern.search(existing):
        return pattern.sub(managed, existing)
    prefix = existing.rstrip()
    return f"{prefix}\n\n{managed}" if prefix else managed


def cmd_init(args: argparse.Namespace) -> None:
    path = config_path()
    if path.exists() and not args.force:
        print(f"Already exists: {path}")
        return
    save_catalog(path, {"version": 1, "shortcuts": {}})
    print(f"Created: {path}")


def cmd_path(_: argparse.Namespace) -> None:
    print(config_path())


def cmd_list(_: argparse.Namespace) -> None:
    catalog = load_catalog(config_path())
    shortcuts = catalog["shortcuts"]
    if not shortcuts:
        print("No shortcuts configured.")
        return
    rows = []
    for name in sorted(shortcuts):
        item = normalize_shortcut(shortcuts[name])
        rows.append([
            name,
            str(item.get("host", "")),
            str(item.get("port", "")),
            str(item.get("user", "")),
            ", ".join(item.get("services", [])),
            str(item.get("description", "")),
        ])
    widths = [max(len(row[i]) for row in rows + [["Name", "Host", "Port", "User", "Services", "Description"]]) for i in range(6)]
    header = ["Name", "Host", "Port", "User", "Services", "Description"]
    print("  ".join(header[i].ljust(widths[i]) for i in range(6)))
    print("  ".join("-" * widths[i] for i in range(6)))
    for row in rows:
        print("  ".join(row[i].ljust(widths[i]) for i in range(6)))


def cmd_show(args: argparse.Namespace) -> None:
    catalog = load_catalog(config_path())
    shortcut = catalog["shortcuts"].get(args.name)
    if not shortcut:
        raise SystemExit(f"Unknown shortcut: {args.name}")
    print(json.dumps(shortcut, indent=2, ensure_ascii=False))
    print()
    print(f"Direct command: {ssh_command(args.name, normalize_shortcut(shortcut))}")


def parse_key_value(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Expected KEY=VALUE: {value}")
        key, raw = value.split("=", 1)
        if not key:
            raise SystemExit(f"Empty key in: {value}")
        result[key] = raw
    return result


def upsert_shortcut(args: argparse.Namespace) -> None:
    require_name(args.name)
    path = config_path()
    catalog = load_catalog(path)
    if args.name in catalog["shortcuts"] and not args.force:
        raise SystemExit(f"{args.name} already exists; pass --force to replace it")
    item: dict[str, Any] = {"host": args.host}
    if args.user:
        item["user"] = args.user
    if args.port:
        item["port"] = args.port
    if args.identity_file:
        item["identity_file"] = args.identity_file
    if args.proxy_jump:
        item["proxy_jump"] = args.proxy_jump
    if args.description:
        item["description"] = args.description
    if args.service:
        item["services"] = args.service
    paths = parse_key_value(args.path or [])
    if paths:
        item["paths"] = paths
    options = parse_key_value(args.option or [])
    if options:
        item["ssh_options"] = options
    catalog["shortcuts"][args.name] = item
    save_catalog(path, catalog)


def cmd_add(args: argparse.Namespace) -> None:
    upsert_shortcut(args)
    print(f"Saved shortcut: {args.name}")


def cmd_render(_: argparse.Namespace) -> None:
    print(render_config(load_catalog(config_path())), end="")


def cmd_install(args: argparse.Namespace) -> None:
    ssh_config = Path(args.ssh_config).expanduser()
    managed = render_config(load_catalog(config_path()))
    existing = ssh_config.read_text(encoding="utf-8") if ssh_config.exists() else ""
    updated = replace_managed_block(existing, managed)
    ssh_config.parent.mkdir(parents=True, exist_ok=True)
    ssh_config.write_text(updated, encoding="utf-8")
    ssh_config.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print(f"Updated: {ssh_config}")


def cmd_find_service(args: argparse.Namespace) -> None:
    term = args.term.lower()
    catalog = load_catalog(config_path())
    matches = []
    for name, shortcut in sorted(catalog["shortcuts"].items()):
        haystack = " ".join([
            name,
            shortcut.get("description", ""),
            " ".join(shortcut.get("services", [])),
        ]).lower()
        if term in haystack:
            matches.append(name)
    if not matches:
        raise SystemExit(f"No shortcuts matched: {args.term}")
    for name in matches:
        shortcut = normalize_shortcut(catalog["shortcuts"][name])
        print(f"{name}: {shortcut.get('user', '')}@{shortcut['host']}:{shortcut.get('port', 22)}")


def cmd_test(args: argparse.Namespace) -> None:
    command = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={args.timeout}", args.name, args.remote_command]
    print(quote_command(command))
    raise SystemExit(subprocess.call(command))


def ensure_key(identity_file: Path, comment: str, generate: bool) -> Path:
    public_file = Path(f"{identity_file}.pub")
    if identity_file.exists() and public_file.exists():
        return public_file
    if not identity_file.exists():
        if not generate:
            raise SystemExit(f"Missing identity file: {identity_file}. Pass --generate-key to create one.")
        identity_file.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(identity_file),
            "-C",
            comment,
            "-N",
            "",
        ])
        identity_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return public_file
    if not public_file.exists():
        public = subprocess.check_output(["ssh-keygen", "-y", "-f", str(identity_file)], text=True)
        public_file.write_text(public, encoding="utf-8")
        public_file.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    return public_file


def run_initial_ssh(args: argparse.Namespace, remote_command: str) -> int:
    command = direct_ssh_base(args)
    command.extend([
        "-o",
        "PreferredAuthentications=publickey,password,keyboard-interactive",
        target_for(args.host, args.user),
        remote_command,
    ])
    env = os.environ.copy()
    secret = env.get("SSH_SHORTCUTS_PASSWORD") or env.get("SSHPASS")
    used_sshpass = False
    if secret:
        sshpass = shutil.which("sshpass")
        if not sshpass:
            raise SystemExit("SSH_SHORTCUTS_PASSWORD/SSHPASS is set, but sshpass is not installed")
        env["SSHPASS"] = secret
        command = [sshpass, "-e"] + command
        used_sshpass = True
    print(quote_command(command[2:] if used_sshpass else command))
    return subprocess.call(command, env=env)


def test_direct_key_login(args: argparse.Namespace) -> int:
    command = direct_ssh_base(args, batch=True)
    command.extend([target_for(args.host, args.user), "true"])
    print(quote_command(command))
    return subprocess.call(command)


def cmd_setup_key(args: argparse.Namespace) -> None:
    original_identity = args.identity_file
    identity = Path(original_identity).expanduser()
    args.identity_file = str(identity)
    comment = args.key_comment or f"ssh-shortcuts:{args.user or 'user'}@{args.host}"
    public_file = ensure_key(identity, comment, args.generate_key)
    public_key = public_file.read_text(encoding="utf-8").strip()
    remote_command = (
        "umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys; "
        f"grep -qxF {shlex.quote(public_key)} ~/.ssh/authorized_keys || "
        f"printf '%s\\n' {shlex.quote(public_key)} >> ~/.ssh/authorized_keys"
    )
    if run_initial_ssh(args, remote_command) != 0:
        raise SystemExit("Failed to install the public key on the remote host")
    if test_direct_key_login(args) != 0:
        raise SystemExit("Public key was installed, but BatchMode key login did not succeed")

    print("Passwordless SSH login is configured.")
    if args.alias:
        add_args = argparse.Namespace(
            name=args.alias,
            host=args.host,
            user=args.user,
            port=args.port,
            identity_file=original_identity if original_identity.startswith("~") else str(identity),
            proxy_jump=args.proxy_jump,
            description=args.description,
            service=args.service,
            path=args.path,
            option=args.option,
            force=args.force,
        )
        upsert_shortcut(add_args)
        print(f"Saved shortcut alias: {args.alias}")
        if args.install_ssh_config:
            cmd_install(argparse.Namespace(ssh_config=str(DEFAULT_SSH_CONFIG)))
        print(f"Connect with: ssh {args.alias}")
    else:
        print("No alias was saved. Ask the user whether to create one, then run the add command if requested.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create an empty private shortcuts config")
    init.add_argument("--force", action="store_true", help="Overwrite an existing config")
    init.set_defaults(func=cmd_init)

    path = sub.add_parser("path", help="Print the private config path")
    path.set_defaults(func=cmd_path)

    list_cmd = sub.add_parser("list", help="List configured shortcuts")
    list_cmd.set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="Show one shortcut")
    show.add_argument("name")
    show.set_defaults(func=cmd_show)

    add = sub.add_parser("add", help="Add or replace a shortcut")
    add.add_argument("name")
    add.add_argument("--host", required=True)
    add.add_argument("--user")
    add.add_argument("--port", type=int)
    add.add_argument("--identity-file")
    add.add_argument("--proxy-jump")
    add.add_argument("--description")
    add.add_argument("--service", action="append")
    add.add_argument("--path", action="append", metavar="KEY=VALUE")
    add.add_argument("--option", action="append", metavar="KEY=VALUE")
    add.add_argument("--force", action="store_true")
    add.set_defaults(func=cmd_add)

    render = sub.add_parser("render-ssh-config", help="Print managed ~/.ssh/config entries")
    render.set_defaults(func=cmd_render)

    install = sub.add_parser("install-ssh-config", help="Install managed entries into ~/.ssh/config")
    install.add_argument("--ssh-config", default=str(DEFAULT_SSH_CONFIG))
    install.set_defaults(func=cmd_install)

    find = sub.add_parser("find-service", help="Find shortcuts by service, name, or description")
    find.add_argument("term")
    find.set_defaults(func=cmd_find_service)

    test = sub.add_parser("test", help="Test an installed SSH shortcut with BatchMode")
    test.add_argument("name")
    test.add_argument("--timeout", type=int, default=5)
    test.add_argument("--remote-command", default="true")
    test.set_defaults(func=cmd_test)

    setup = sub.add_parser("setup-key", help="Install an SSH public key after first password login")
    setup.add_argument("--host", required=True)
    setup.add_argument("--user")
    setup.add_argument("--port", type=int)
    setup.add_argument("--identity-file", default=str(DEFAULT_IDENTITY))
    setup.add_argument("--proxy-jump")
    setup.add_argument("--generate-key", action="store_true", help="Create the identity file if it does not exist")
    setup.add_argument("--key-comment")
    setup.add_argument("--alias", help="Save this host as a shortcut alias after key login succeeds")
    setup.add_argument("--description")
    setup.add_argument("--service", action="append")
    setup.add_argument("--path", action="append", metavar="KEY=VALUE")
    setup.add_argument("--option", action="append", metavar="KEY=VALUE")
    setup.add_argument("--force", action="store_true")
    setup.add_argument("--install-ssh-config", action="store_true", help="Update ~/.ssh/config after saving --alias")
    setup.set_defaults(func=cmd_setup_key)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
