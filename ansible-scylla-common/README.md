# ansible-scylla-common

A common role providing shared tasks and utilities for all Scylla Ansible roles.

## Features

- Firewall deactivation (supports firewalld, iptables, ufw)
- Common utilities and tasks used across Scylla roles

## Variables

- `disable_firewall`: Whether firewall should be disabled. (default: false)

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
