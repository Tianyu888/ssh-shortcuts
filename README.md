# SSH Shortcuts

English | [中文](#中文)

SSH Shortcuts is a public Codex skill for managing user-defined SSH shortcut catalogs safely. It helps Codex create, inspect, render, and test SSH aliases without putting private infrastructure data inside the skill repository.

The skill stores real host data in a private local config file:

```text
~/.config/ssh-shortcuts/shortcuts.json
```

## What It Does

- Manage SSH aliases from a private local JSON catalog.
- Generate a managed block for `~/.ssh/config`.
- Support jump hosts through `ProxyJump`.
- Search hosts by shortcut name, description, or service.
- Keep public skill files free of private IPs, passwords, host inventories, and service secrets.

## Install

Clone this repository into your Codex skills directory:

```bash
git clone git@github.com:Tianyu888/ssh-shortcuts.git ~/.codex/skills/ssh-shortcuts
```

If you use HTTPS:

```bash
git clone https://github.com/Tianyu888/ssh-shortcuts.git ~/.codex/skills/ssh-shortcuts
```

Then invoke it in Codex with:

```text
$ssh-shortcuts
```

## Quick Start

Create your private config:

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py init
```

Add a shortcut:

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py add prod-api \
  --host 203.0.113.10 \
  --user ubuntu \
  --port 22 \
  --identity-file ~/.ssh/prod_api \
  --description "Production API server" \
  --service api \
  --service nginx \
  --path app=/srv/app
```

List shortcuts:

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py list
```

Render SSH config:

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py render-ssh-config
```

Install the managed block into `~/.ssh/config`:

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py install-ssh-config
```

Test a shortcut:

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py test prod-api
```

## Config Example

```json
{
  "version": 1,
  "shortcuts": {
    "prod-api": {
      "host": "203.0.113.10",
      "port": 22,
      "user": "ubuntu",
      "identity_file": "~/.ssh/prod_api",
      "description": "Production API server",
      "services": ["api", "nginx"],
      "paths": {
        "app": "/srv/app"
      }
    }
  }
}
```

See [references/config-schema.md](references/config-schema.md) for the full schema.

## Safety

Do not store these values in this repository or in your shortcut config:

- Passwords or passphrases.
- Private key contents.
- API tokens, cookies, database credentials, SMTP credentials, or cloud credentials.
- Any infrastructure inventory you do not intend to share.

Use SSH keys, `ssh-agent`, hardware keys, or your operating system keychain for authentication.

## 中文

SSH Shortcuts 是一个公开的 Codex skill，用来安全地管理用户自己的 SSH shortcut。它可以帮助 Codex 创建、查看、生成和测试 SSH alias，但不会把你的真实服务器信息写进 skill 仓库。

真实主机数据默认保存在用户本机私有配置中：

```text
~/.config/ssh-shortcuts/shortcuts.json
```

## 功能

- 用本地私有 JSON 配置管理 SSH alias。
- 为 `~/.ssh/config` 生成受控配置块。
- 通过 `ProxyJump` 支持跳板机。
- 按 shortcut 名称、描述或服务名查找服务器。
- 避免在公开 skill 文件里保存私有 IP、密码、主机清单或服务密钥。

## 安装

把仓库 clone 到 Codex skills 目录：

```bash
git clone git@github.com:Tianyu888/ssh-shortcuts.git ~/.codex/skills/ssh-shortcuts
```

也可以使用 HTTPS：

```bash
git clone https://github.com/Tianyu888/ssh-shortcuts.git ~/.codex/skills/ssh-shortcuts
```

之后在 Codex 中这样调用：

```text
$ssh-shortcuts
```

## 快速开始

创建私有配置：

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py init
```

添加 shortcut：

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py add prod-api \
  --host 203.0.113.10 \
  --user ubuntu \
  --port 22 \
  --identity-file ~/.ssh/prod_api \
  --description "Production API server" \
  --service api \
  --service nginx \
  --path app=/srv/app
```

查看 shortcut 列表：

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py list
```

生成 SSH config：

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py render-ssh-config
```

写入受控配置块到 `~/.ssh/config`：

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py install-ssh-config
```

测试 shortcut：

```bash
python3 ~/.codex/skills/ssh-shortcuts/scripts/ssh_shortcuts.py test prod-api
```

## 配置示例

```json
{
  "version": 1,
  "shortcuts": {
    "prod-api": {
      "host": "203.0.113.10",
      "port": 22,
      "user": "ubuntu",
      "identity_file": "~/.ssh/prod_api",
      "description": "Production API server",
      "services": ["api", "nginx"],
      "paths": {
        "app": "/srv/app"
      }
    }
  }
}
```

完整配置格式见 [references/config-schema.md](references/config-schema.md)。

## 安全边界

不要把以下内容保存到这个仓库，也不要写进 shortcut 配置：

- 密码或密钥口令。
- 私钥文件内容。
- API token、Cookie、数据库凭据、SMTP 凭据或云服务凭据。
- 任何你不打算公开的基础设施清单。

认证建议使用 SSH key、`ssh-agent`、硬件密钥或操作系统密钥管理工具。
