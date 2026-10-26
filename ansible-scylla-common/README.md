# ansible-scylla-common

A common role providing shared tasks and utilities for all Scylla Ansible roles.

## Features

- Firewall handling (disable firewalld/iptables/ufw, or apply persisted INPUT DROP sources)
- Common utilities and tasks used across Scylla roles
- Running CQL as a user or over the maintenance socket (`run_cqlsh.yml`)

## Variables

- `disable_firewall`: Whether firewall should be disabled. (default: true, unless deprecated `firewall_enabled` is true)
- `iptables_drop_sources`: List of source IPs to DROP on INPUT when `disable_firewall` is false. (default: `[]`)
  Each run reconciles the INPUT chain to match this list exactly: sources present are
  added, and any previously-applied DROP source no longer in the list is removed.

## Tasks

### `run_cqlsh.yml`

Runs a CQL statement with `cqlsh`, logging in as a user, or over the node's
[maintenance socket](https://docs.scylladb.com/manual/stable/operating-scylla/admin-tools/maintenance-socket.html)
when no user is given. The socket accepts CQL without authentication, which is how the first superuser gets created
now that ScyllaDB has no default one (starting from 2026.2). The caller passes the path of the socket, and the task
fails with a message saying what to enable if it does not exist.

```yaml
- import_role:
    name: ansible-scylla-common
    tasks_from: run_cqlsh.yml
  vars:
    cql_statement: "CREATE ROLE admin WITH SUPERUSER = true AND LOGIN = true AND PASSWORD = 'secret';"
    cql_maintenance_socket: /var/lib/scylla/cql.m   # used because there is no cql_username
```

To log in as a user instead, set `cql_username`, `cql_password` and `cql_host` (and `cql_port` if it is not 9042).

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
