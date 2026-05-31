# cli-anything-jumpserver

Stateful CLI harness for [JumpServer](https://www.jumpserver.com/) bastion host management.

## Installation

```bash
cd agent-harness
pip install -e .
```

## Quick Start

```bash
# Login to your JumpServer instance
cli-anything-jumpserver auth login --url https://jumpserver.example.com --username admin

# List host assets
cli-anything-jumpserver asset list --type host

# Search users
cli-anything-jumpserver user list --search admin

# View active sessions
cli-anything-jumpserver session list --active

# Start interactive REPL mode
cli-anything-jumpserver --interactive
```

## Usage

### Authentication

```bash
# Login
cli-anything-jumpserver auth login --url <URL> --username <USER> --password <PASS>

# Check session status
cli-anything-jumpserver auth status

# Switch organization (multi-org)
cli-anything-jumpserver auth org <ORG_ID>

# List organizations
cli-anything-jumpserver auth org --list

# Logout
cli-anything-jumpserver auth logout
```

### Asset Management

```bash
# List assets by type
cli-anything-jumpserver asset list --type host
cli-anything-jumpserver asset list --type device
cli-anything-jumpserver asset list --type database

# Get asset details
cli-anything-jumpserver asset get <ASSET_ID> --type host

# Create asset
cli-anything-jumpserver asset create --name "web-01" --address 192.168.1.10 --platform 1

# Update asset
cli-anything-jumpserver asset update <ASSET_ID> --comment "Production server"

# Delete asset
cli-anything-jumpserver asset delete <ASSET_ID> --force

# Manage nodes
cli-anything-jumpserver asset node list --tree
cli-anything-jumpserver asset node create --name "Production" --parent <PARENT_ID>
cli-anything-jumpserver asset node add-assets <NODE_ID> --assets "id1,id2"

# Platforms
cli-anything-jumpserver asset platform list

# Gateways and zones
cli-anything-jumpserver asset gateway list
cli-anything-jumpserver asset gateway test <GATEWAY_ID>
cli-anything-jumpserver asset zone list
```

### User Management

```bash
# List users
cli-anything-jumpserver user list --search admin

# Create user
cli-anything-jumpserver user create --name "John Doe" --username jdoe --email jdoe@example.com

# Reset password
cli-anything-jumpserver user reset-password <USER_ID> --password "new-password"

# Unblock user
cli-anything-jumpserver user unblock <USER_ID>

# Current user profile
cli-anything-jumpserver user profile

# My accessible assets
cli-anything-jumpserver user my-assets

# User groups
cli-anything-jumpserver user group list
cli-anything-jumpserver user group create --name "DevOps Team"
cli-anything-jumpserver user group members <GROUP_ID>
```

### Permissions

```bash
# List permissions
cli-anything-jumpserver perm list

# Create permission
cli-anything-jumpserver perm create --name "Dev access" --users "id1,id2" --assets "id1,id2"

# View authorized users/assets
cli-anything-jumpserver perm users <PERM_ID>
cli-anything-jumpserver perm assets <PERM_ID>
```

### Accounts

```bash
# List accounts
cli-anything-jumpserver account list --asset <ASSET_ID>

# Create account
cli-anything-jumpserver account create --asset <ASSET_ID> --username root --secret-type password

# View secret (requires permission)
cli-anything-jumpserver account secret view <ACCOUNT_ID>

# Password history
cli-anything-jumpserver account secret history <ACCOUNT_ID>

# Account templates
cli-anything-jumpserver account template list
```

### Sessions

```bash
# List sessions
cli-anything-jumpserver session list --active
cli-anything-jumpserver session list --protocol ssh

# Session replay
cli-anything-jumpserver session replay <SESSION_ID>

# Kill session
cli-anything-jumpserver session kill <SESSION_ID> --force

# Command history
cli-anything-jumpserver session command list --session <SESSION_ID>
cli-anything-jumpserver session command list --risk 5

# Terminal status
cli-anything-jumpserver session terminal list
cli-anything-jumpserver session terminal status <TERMINAL_ID>
```

### Audit & Operations

```bash
# Login logs
cli-anything-jumpserver audit login --status failed

# Operation logs
cli-anything-jumpserver audit operate --action delete --resource Asset

# FTP logs
cli-anything-jumpserver audit ftp

# Password change logs
cli-anything-jumpserver audit password

# Jobs
cli-anything-jumpserver ops job-list
cli-anything-jumpserver ops job-log <EXECUTION_ID>

# Playbooks
cli-anything-jumpserver ops playbook-list
```

### System

```bash
# System settings
cli-anything-jumpserver system settings

# Health check
cli-anything-jumpserver system health

# System info
cli-anything-jumpserver system info
```

### Output Formats

All commands support multiple output formats:

```bash
# Table (default)
cli-anything-jumpserver asset list

# JSON (for scripts/agents)
cli-anything-jumpserver asset list --output json
cli-anything-jumpserver asset list -o json

# YAML
cli-anything-jumpserver asset list --output yaml

# Custom columns
cli-anything-jumpserver asset list --columns "name,address,platform,is_active"
```

### Dry Run Mode

All mutation commands support `--dry-run` to preview operations:

```bash
cli-anything-jumpserver asset create --name test --address 10.0.0.1 --platform 1 --dry-run
cli-anything-jumpserver user delete <ID> --dry-run
```

### Environment Variables

- `JUMPSERVER_URL` - Default JumpServer URL
- `JUMPSERVER_USERNAME` - Default username
- `JUMPSERVER_PASSWORD` - Default password

### REPL Mode

Launch interactive mode for multiple commands:

```bash
cli-anything-jumpserver --interactive
# or
cli-anything-jumpserver -i
```

In REPL, you can use Tab completion and type commands directly:
```
jumpserver> auth login --url https://js.example.com --username admin
✓ Login successful. Session saved.
jumpserver> asset list --type host --search web
jumpserver> session list --active
jumpserver> exit
```
