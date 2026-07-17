# ansible-scylla-common

A common role providing shared tasks and utilities for all Scylla Ansible roles.

## Features

- Firewall handling (disable firewalld/iptables/ufw, or apply persisted INPUT DROP sources)
- Common utilities and tasks used across Scylla roles

## Variables

- `disable_firewall`: Whether firewall should be disabled. (default: true, unless deprecated `firewall_enabled` is true)
- `iptables_drop_sources`: List of source IPs to DROP on INPUT when `disable_firewall` is false. (default: `[]`)

## Usage

Include this role as a dependency in other Scylla roles:

```yaml
dependencies:
  - role: ansible-scylla-common
```

Or include it in your playbook:

```yaml
- hosts: all
  roles:
    - ansible-scylla-common
```
