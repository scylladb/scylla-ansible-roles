#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

import os
import re
import shutil
import stat
import tempfile

from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type

DOCUMENTATION = r'''
---
module: scylla_cqlsh
short_description: Run CQL statements on a ScyllaDB node as a superuser
description:
- Runs CQL statements with C(cqlsh) on the node the module executes on.
- It logs in either with a username and a password, or over the maintenance socket of the node.
- The maintenance socket is a Unix domain socket that accepts CQL without authentication and with full
  permissions. ScyllaDB has no default superuser starting from 2026.2, and the maintenance socket is how the
  first one gets created.
- The path of the socket is resolved from the C(maintenance_socket) and C(workdir) options of the
  scylla.yaml of the node.
  See U(https://docs.scylladb.com/manual/stable/operating-scylla/admin-tools/maintenance-socket.html).
options:
  statements:
    description:
    - CQL statements to run, in order. A terminating C(;) is added to the statements that lack one.
    type: list
    elements: str
    required: true
  login:
    description:
    - How to log in.
    - C(credentials) logs in with I(username) and I(password).
    - C(maintenance_socket) uses the maintenance socket, and fails when the node has none.
    - C(auto) uses the maintenance socket when the node has one, and I(username) and I(password) otherwise.
    type: str
    choices: [auto, credentials, maintenance_socket]
    default: auto
  username:
    description:
    - User to log in as. Required together with I(password).
    type: str
  password:
    description:
    - Password of I(username). It is given to C(cqlsh) with C(-p), so it is visible in the process list while
      C(cqlsh) runs. Logging in over the maintenance socket needs no password.
    type: str
  host:
    description:
    - Address to connect to when logging in with credentials.
    type: str
    default: 127.0.0.1
  port:
    description:
    - Port to connect to when logging in with credentials.
    type: int
    default: 9042
  scylla_yaml:
    description:
    - Path of the scylla.yaml the maintenance socket is resolved from.
    type: path
    default: /etc/scylla/scylla.yaml
  cqlsh:
    description:
    - Name or path of the C(cqlsh) executable.
    type: str
    default: cqlsh
notes:
- Supports check mode, in which the login is resolved but no statement is run.
- The statements are part of the task output. Set C(no_log) on tasks whose statements carry secrets.
'''

EXAMPLES = r'''
- name: Create the first superuser over the maintenance socket
  scylla_cqlsh:
    login: maintenance_socket
    statements:
      - "CREATE ROLE admin WITH SUPERUSER = true AND LOGIN = true AND PASSWORD = 'secret';"

- name: Adjust replication as an existing superuser
  scylla_cqlsh:
    login: credentials
    host: 10.0.0.1
    username: admin
    password: secret
    statements:
      - "ALTER KEYSPACE system_auth WITH replication = {'class': 'NetworkTopologyStrategy', 'dc1': 3};"
'''

RETURN = r'''
login:
  description: How the statements were run. Also present when running them failed.
  returned: when a login was selected
  type: str
  sample: maintenance_socket
socket:
  description: Path of the maintenance socket.
  returned: when I(login) is C(maintenance_socket)
  type: str
  sample: /var/lib/scylla/cql.m
rc:
  description: Exit status of C(cqlsh).
  returned: when cqlsh was run
  type: int
stdout:
  description: Standard output of C(cqlsh).
  returned: when cqlsh was run
  type: str
stderr:
  description: Standard error of C(cqlsh).
  returned: when cqlsh was run
  type: str
'''

DEFAULT_SCYLLA_YAML = '/etc/scylla/scylla.yaml'
DEFAULT_WORKDIR = '/var/lib/scylla'
# ScyllaDB 2026.2 defaults 'maintenance_socket' to 'workdir'. Older versions default it to 'ignore', so on them
# the path an absent option resolves to holds no socket.
DEFAULT_MAINTENANCE_SOCKET = 'workdir'
SOCKET_FILE_NAME = 'cql.m'

# What recent cqlsh versions print when given a password with -p. It says nothing about why a run failed, and would
# otherwise be the first thing a failure message shows.
CQLSH_PASSWORD_WARNING = re.compile(
    r'^(Warning: Using a password on the command line|Recommendation: use the credentials)')

LOGIN_AUTO = 'auto'
LOGIN_CREDENTIALS = 'credentials'
LOGIN_MAINTENANCE_SOCKET = 'maintenance_socket'


class LoginError(Exception):
    """
    Raised when no way of logging in matches the requested login mode.
    """


def read_option(config_text, name):
    """
    Reads a top-level scalar option of a scylla.yaml.

    Only options written as ``name: value`` on a single line are understood, which is all the options this
    module needs.

    :param config_text: Contents of the scylla.yaml.
    :param name: Name of the option.
    :return: The value of the option without quotes and trailing comments, or None when the option is not set
             or empty.
    """
    match = re.search(r'^%s:[ \t]*(.*)$' % re.escape(name), config_text, re.MULTILINE)
    if match is None:
        return None

    value = match.group(1).strip()
    if value[:1] in ('"', "'"):
        closing = value.find(value[0], 1)
        value = value[1:closing] if closing != -1 else value[1:]
    else:
        value = re.split(r'(?:^|\s)#', value, maxsplit=1)[0].strip()

    return value or None


def resolve_maintenance_socket(config_text):
    """
    Works out where the maintenance socket of a node is, the way ScyllaDB does.

    :param config_text: Contents of the scylla.yaml of the node.
    :return: Path of the maintenance socket, or None when the node is configured not to open one.
    """
    setting = read_option(config_text, 'maintenance_socket') or DEFAULT_MAINTENANCE_SOCKET
    if setting == 'ignore':
        return None

    if setting == 'workdir':
        return os.path.join(read_option(config_text, 'workdir') or DEFAULT_WORKDIR, SOCKET_FILE_NAME)

    return setting


def is_socket(path):
    """
    Tells whether a path is a Unix domain socket.

    :param path: Path to check.
    :return: True if the path exists and is a socket.
    """
    try:
        return stat.S_ISSOCK(os.stat(path).st_mode)
    except OSError:
        return False


def describe_missing_socket(socket_path):
    """
    Explains why a node has no usable maintenance socket.

    :param socket_path: Path of the maintenance socket of the node, or None when it is configured away.
    :return: The reason, as a phrase to put in a message.
    """
    if socket_path is None:
        return "'maintenance_socket' is 'ignore' in scylla.yaml"

    return "there is no maintenance socket at %s" % socket_path


def select_login(login, socket_path, has_credentials):
    """
    Picks how to log in out of what was asked for and what the node offers.

    :param login: Requested login mode, one of LOGIN_AUTO, LOGIN_CREDENTIALS and LOGIN_MAINTENANCE_SOCKET.
    :param socket_path: Path of the maintenance socket of the node, or None when it is configured away.
    :param has_credentials: Whether a username and a password were given.
    :return: LOGIN_CREDENTIALS or LOGIN_MAINTENANCE_SOCKET.
    :raises LoginError: If the requested login mode cannot be satisfied.
    """
    if login == LOGIN_CREDENTIALS:
        if not has_credentials:
            raise LoginError("login=credentials needs a username and a password")
        return LOGIN_CREDENTIALS

    if socket_path is not None and is_socket(socket_path):
        return LOGIN_MAINTENANCE_SOCKET

    if login == LOGIN_AUTO and has_credentials:
        return LOGIN_CREDENTIALS

    message = "Cannot log in over the maintenance socket: %s. Enable 'maintenance_socket' in scylla.yaml and " \
              "restart the node" % describe_missing_socket(socket_path)
    if login == LOGIN_AUTO:
        message += ", or give a username and a password"

    raise LoginError(message)


def normalize_statements(statements):
    """
    Cleans up the statements to run.

    :param statements: The statements as given to the module.
    :return: The statements without surrounding whitespace and empty ones, each ending with a semicolon.
    """
    cleaned = [statement.strip() for statement in statements]
    return [statement if statement.endswith(';') else statement + ';' for statement in cleaned if statement]


def write_private_file(path, content):
    """
    Creates a file only its owner can read.

    :param path: Path of the file, which must not exist.
    :param content: Text to write to it.
    """
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as handle:
        handle.write(content)


def run_cqlsh(module, cqlsh, login, socket_path, host, port, username, password, statements):
    """
    Runs statements with cqlsh.

    The statements go through a file in a private temporary directory, so they do not show up in the process list
    and need no shell quoting.

    :param module: The AnsibleModule, used to run the command.
    :param cqlsh: Name or path of the cqlsh executable.
    :param login: LOGIN_CREDENTIALS or LOGIN_MAINTENANCE_SOCKET.
    :param socket_path: Path of the maintenance socket, used when logging in over it.
    :param host: Address to connect to when logging in with credentials.
    :param port: Port to connect to when logging in with credentials.
    :param username: User to log in as when logging in with credentials.
    :param password: Password of the user when logging in with credentials.
    :param statements: Statements to run, each already terminated by a semicolon.
    :return: The exit status, standard output and standard error of cqlsh.
    """
    scratch = tempfile.mkdtemp(prefix='scylla_cqlsh_')
    try:
        script = os.path.join(scratch, 'statements.cql')
        write_private_file(script, '\n'.join(statements) + '\n')

        if login == LOGIN_CREDENTIALS:
            command = [cqlsh, host, str(port), '-u', username, '-p', password, '-f', script]
        else:
            command = [cqlsh, socket_path, '-f', script]

        return module.run_command(command)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def describe_failure(rc, stdout, stderr):
    """
    Builds the message of a failed cqlsh run.

    :param rc: Exit status of cqlsh.
    :param stdout: Standard output of cqlsh.
    :param stderr: Standard error of cqlsh.
    :return: The exit status and what cqlsh said about the failure, without its warnings about passwords.
    """
    details = '\n'.join(line for line in stderr.splitlines() if not CQLSH_PASSWORD_WARNING.match(line)).strip()
    return "cqlsh exited with status %d: %s" % (rc, details or stdout.strip())


def read_config(path):
    """
    Reads the scylla.yaml of the node.

    :param path: Path of the scylla.yaml.
    :return: Its contents, or an empty string when it does not exist, which makes every option take its default.
    :raises IOError: If it exists but cannot be read.
    """
    try:
        with open(path) as handle:
            return handle.read()
    except (IOError, OSError) as error:
        if error.errno == 2:
            return ''
        raise


def main():
    """
    Entry point of the module.
    """
    module = AnsibleModule(
        argument_spec=dict(
            statements=dict(type='list', elements='str', required=True),
            login=dict(type='str', default=LOGIN_AUTO,
                       choices=[LOGIN_AUTO, LOGIN_CREDENTIALS, LOGIN_MAINTENANCE_SOCKET]),
            username=dict(type='str'),
            password=dict(type='str', no_log=True),
            host=dict(type='str', default='127.0.0.1'),
            port=dict(type='int', default=9042),
            scylla_yaml=dict(type='path', default=DEFAULT_SCYLLA_YAML),
            cqlsh=dict(type='str', default='cqlsh'),
        ),
        required_together=[['username', 'password']],
        supports_check_mode=True,
    )
    params = module.params

    statements = normalize_statements(params['statements'])
    if not statements:
        module.fail_json(msg="'statements' must contain at least one statement")

    socket_path = None
    if params['login'] != LOGIN_CREDENTIALS:
        try:
            socket_path = resolve_maintenance_socket(read_config(params['scylla_yaml']))
        except (IOError, OSError) as error:
            module.fail_json(msg="Cannot read %s: %s" % (params['scylla_yaml'], error))

    try:
        login = select_login(params['login'], socket_path, params['username'] is not None)
    except LoginError as error:
        module.fail_json(msg=str(error))

    result = dict(login=login)
    if login == LOGIN_MAINTENANCE_SOCKET:
        result['socket'] = socket_path
    elif params['login'] == LOGIN_AUTO:
        module.warn("Not using the maintenance socket: %s. Logging in with the given credentials."
                    % describe_missing_socket(socket_path))

    if module.check_mode:
        module.exit_json(changed=False, msg="Skipped in check mode", **result)

    rc, stdout, stderr = run_cqlsh(module, params['cqlsh'], login, socket_path, params['host'], params['port'],
                                   params['username'], params['password'], statements)
    result.update(rc=rc, stdout=stdout, stderr=stderr)

    if rc != 0:
        module.fail_json(msg=describe_failure(rc, stdout, stderr), **result)

    module.exit_json(changed=True, **result)


if __name__ == '__main__':
    main()
