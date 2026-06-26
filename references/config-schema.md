# SSH Shortcuts Config Schema

The default config is private user data at:

```text
~/.config/ssh-shortcuts/shortcuts.json
```

Users may override it for one command with:

```bash
SSH_SHORTCUTS_CONFIG=/path/to/shortcuts.json python3 scripts/ssh_shortcuts.py list
```

## JSON Shape

```json
{
  "version": 1,
  "shortcuts": {
    "prod-api": {
      "host": "203.0.113.10",
      "port": 22,
      "user": "ubuntu",
      "identity_file": "~/.ssh/prod_api",
      "proxy_jump": "bastion",
      "description": "Production API server",
      "services": ["api", "nginx"],
      "paths": {
        "app": "/srv/app",
        "logs": "/var/log/nginx"
      },
      "ssh_options": {
        "IdentitiesOnly": "yes",
        "ServerAliveInterval": "30"
      },
      "notes": [
        "Human-readable operational notes that do not contain secrets."
      ]
    }
  }
}
```

## Fields

- `host`: Required. Hostname or IP address for `HostName`.
- `user`: Optional. SSH username.
- `port`: Optional. SSH port. Defaults to OpenSSH behavior when omitted.
- `identity_file`: Optional. Path to the public reference of a private key, such as `~/.ssh/id_ed25519`.
- `proxy_jump`: Optional. Value for `ProxyJump`, usually another shortcut or `user@host:port`.
- `description`: Optional. Short human summary.
- `services`: Optional list of service names deployed or managed on the host.
- `paths`: Optional object of named important paths.
- `ssh_options`: Optional object of extra OpenSSH config options.
- `notes`: Optional list of non-secret operational notes.

## Do Not Store

- Passwords or passphrases.
- Private key contents.
- API tokens, cookies, database credentials, SMTP credentials, or cloud credentials.
- Personal host inventories intended to remain private inside a public skill repository.

## Managed SSH Config Block

`install-ssh-config` updates only this block inside `~/.ssh/config`:

```sshconfig
# BEGIN ssh-shortcuts managed
Host prod-api
    HostName 203.0.113.10
    User ubuntu
    Port 22
    IdentityFile ~/.ssh/prod_api
    IdentitiesOnly yes
    ProxyJump bastion
# END ssh-shortcuts managed
```

Manual entries outside the markers are preserved.
