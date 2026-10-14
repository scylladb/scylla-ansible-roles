# ansible-scylla-common

A common role providing shared tasks and utilities for all Scylla Ansible roles.

## Features

- Firewall handling (disable firewalld/iptables/ufw, or apply persisted INPUT DROP sources)
- Common utilities and tasks used across Scylla roles
- `scylla_cqlsh` module to run CQL statements as a superuser

## Variables

- `disable_firewall`: Whether firewall should be disabled. (default: true, unless deprecated `firewall_enabled` is true)
- `iptables_drop_sources`: List of source IPs to DROP on INPUT when `disable_firewall` is false. (default: `[]`)
  Each run reconciles the INPUT chain to match this list exactly: sources present are
  added, and any previously-applied DROP source no longer in the list is removed.

## Modules

### `scylla_cqlsh`

Runs CQL statements with `cqlsh` on the node it executes on, logging in with a username and a password or over
the node's [maintenance socket](https://docs.scylladb.com/manual/stable/operating-scylla/admin-tools/maintenance-socket.html).
The socket needs no credentials, which is how the first superuser gets created now that ScyllaDB has no default
one (starting from 2026.2). Its path is resolved from `maintenance_socket` and `workdir` in the node's `scylla.yaml`.

```yaml
- name: Create the first superuser
  scylla_cqlsh:
    login: maintenance_socket
    statements:
      - "CREATE ROLE admin WITH SUPERUSER = true AND LOGIN = true AND PASSWORD = 'secret';"
  become: true
```

`login` is `credentials`, `maintenance_socket` or `auto` (the socket when the node has one, the credentials
otherwise). Run `ansible-doc -t module scylla_cqlsh` for all the options. Unit tests:
`python -m unittest discover -s ansible-scylla-common/tests`.

The module is found by the roles that depend on this one. A playbook outside a role can reach it through a
`library` directory next to it that links to `ansible-scylla-common/library`.

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
