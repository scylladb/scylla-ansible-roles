import json
import os
import shutil
import socket
import stat
import sys
import tempfile
import unittest
from unittest import mock

from ansible.module_utils import basic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'library'))

import scylla_cqlsh  # noqa: E402


class ModuleExit(Exception):
    """
    Stands in for AnsibleModule.exit_json and fail_json, which end the process.
    """

    def __init__(self, failed, result):
        super().__init__(result)
        self.failed = failed
        self.result = result


class ReadOptionTest(unittest.TestCase):
    def test_plain_value(self):
        self.assertEqual(scylla_cqlsh.read_option("workdir: /data/scylla\n", 'workdir'), '/data/scylla')

    def test_quoted_value_keeps_hash_and_spaces(self):
        self.assertEqual(scylla_cqlsh.read_option("workdir: '/data/a #b'  # note\n", 'workdir'), '/data/a #b')
        self.assertEqual(scylla_cqlsh.read_option('workdir: "/data/x"\n', 'workdir'), '/data/x')

    def test_trailing_comment_is_dropped(self):
        self.assertEqual(scylla_cqlsh.read_option("workdir: /data/scylla  # where\n", 'workdir'), '/data/scylla')

    def test_absent_commented_out_and_empty_options_are_none(self):
        text = "# workdir: /commented\nother: 1\nmaintenance_socket:\nmaintenance_socket_group: x\n"
        self.assertIsNone(scylla_cqlsh.read_option(text, 'workdir'))
        self.assertIsNone(scylla_cqlsh.read_option(text, 'maintenance_socket'))

    def test_name_is_matched_exactly(self):
        self.assertIsNone(scylla_cqlsh.read_option("maintenance_socket_group: scylla\n", 'maintenance_socket'))


class ResolveMaintenanceSocketTest(unittest.TestCase):
    def test_absent_option_means_workdir_with_default_workdir(self):
        self.assertEqual(scylla_cqlsh.resolve_maintenance_socket(""), '/var/lib/scylla/cql.m')

    def test_workdir_is_taken_from_the_config(self):
        text = "maintenance_socket: workdir\nworkdir: /data/scylla\n"
        self.assertEqual(scylla_cqlsh.resolve_maintenance_socket(text), '/data/scylla/cql.m')

    def test_ignore_means_no_socket(self):
        self.assertIsNone(scylla_cqlsh.resolve_maintenance_socket("maintenance_socket: ignore\nworkdir: /data\n"))

    def test_explicit_path_is_used_as_is(self):
        self.assertEqual(scylla_cqlsh.resolve_maintenance_socket("maintenance_socket: /run/scylla.sock\n"),
                         '/run/scylla.sock')


class SocketTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='sc')
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def make_socket(self, name='cql.m'):
        path = os.path.join(self.tmp, name)
        listener = socket.socket(socket.AF_UNIX)
        self.addCleanup(listener.close)
        listener.bind(path)
        return path


class SelectLoginTest(SocketTestCase):
    def test_credentials_never_look_at_the_socket(self):
        self.assertEqual(scylla_cqlsh.select_login('credentials', self.make_socket(), True), 'credentials')

    def test_credentials_need_credentials(self):
        with self.assertRaisesRegex(scylla_cqlsh.LoginError, 'needs a username and a password'):
            scylla_cqlsh.select_login('credentials', None, False)

    def test_socket_login_uses_an_existing_socket(self):
        self.assertEqual(scylla_cqlsh.select_login('maintenance_socket', self.make_socket(), True),
                         'maintenance_socket')

    def test_socket_login_without_socket_says_how_to_enable_it(self):
        with self.assertRaisesRegex(scylla_cqlsh.LoginError, "'maintenance_socket' is 'ignore'.*restart the node$"):
            scylla_cqlsh.select_login('maintenance_socket', None, True)

        missing = os.path.join(self.tmp, 'nope')
        with self.assertRaisesRegex(scylla_cqlsh.LoginError, 'no maintenance socket at %s' % missing):
            scylla_cqlsh.select_login('maintenance_socket', missing, True)

    def test_a_regular_file_is_not_a_socket(self):
        path = os.path.join(self.tmp, 'cql.m')
        open(path, 'w').close()
        with self.assertRaises(scylla_cqlsh.LoginError):
            scylla_cqlsh.select_login('maintenance_socket', path, False)

    def test_auto_prefers_the_socket(self):
        self.assertEqual(scylla_cqlsh.select_login('auto', self.make_socket(), True), 'maintenance_socket')

    def test_auto_falls_back_to_credentials(self):
        self.assertEqual(scylla_cqlsh.select_login('auto', None, True), 'credentials')
        self.assertEqual(scylla_cqlsh.select_login('auto', os.path.join(self.tmp, 'nope'), True), 'credentials')

    def test_auto_without_either_mentions_both_ways_out(self):
        with self.assertRaisesRegex(scylla_cqlsh.LoginError, 'or give a username and a password$'):
            scylla_cqlsh.select_login('auto', None, False)


class DescribeFailureTest(unittest.TestCase):
    def test_drops_the_password_warning_of_cqlsh(self):
        stderr = ("Warning: Using a password on the command line interface can be insecure.\n"
                  "Recommendation: use the credentials file to securely provide the password.\n\n"
                  "Connection error: ('Unable to connect to any servers',)\n")
        self.assertEqual(scylla_cqlsh.describe_failure(1, '', stderr),
                         "cqlsh exited with status 1: Connection error: ('Unable to connect to any servers',)")

    def test_falls_back_to_stdout(self):
        self.assertEqual(scylla_cqlsh.describe_failure(2, 'oops\n', "Warning: Using a password on the command line\n"),
                         "cqlsh exited with status 2: oops")


class NormalizeStatementsTest(unittest.TestCase):
    def test_terminates_trims_and_drops_empty_statements(self):
        self.assertEqual(scylla_cqlsh.normalize_statements(["  SELECT 1  ", "", "  ", "DROP ROLE x;"]),
                         ["SELECT 1;", "DROP ROLE x;"])


class ModuleTest(SocketTestCase):
    def setUp(self):
        super().setUp()
        self.yaml = os.path.join(self.tmp, 'scylla.yaml')
        self.calls = []
        self.warnings = []

    def write_yaml(self, text):
        with open(self.yaml, 'w') as handle:
            handle.write(text)

    @staticmethod
    def read(path):
        with open(path) as handle:
            return handle.read()

    def run_module(self, args, outcome=(0, 'done', ''), check_mode=False):
        """
        Runs main() with the given module arguments and a fake cqlsh.

        What cqlsh would have seen (the command and the contents of the script it is given) is recorded in
        self.calls while the temporary directory still exists.

        :param args: Module arguments.
        :param outcome: (rc, stdout, stderr) the fake cqlsh returns.
        :param check_mode: Whether to run in check mode.
        :return: The ModuleExit raised when the module finished.
        """
        def fake_run_command(command, **kwargs):
            script_path = command[command.index('-f') + 1]
            self.calls.append(dict(command=command, script_path=script_path, script=self.read(script_path),
                                   script_mode=stat.S_IMODE(os.stat(script_path).st_mode)))
            return outcome

        def finish(failed):
            def raiser(*unused, **result):
                raise ModuleExit(failed, result)
            return raiser

        args = dict(args, scylla_yaml=self.yaml, _ansible_check_mode=check_mode)
        basic._ANSIBLE_ARGS = json.dumps({'ANSIBLE_MODULE_ARGS': args}).encode()
        with mock.patch.object(basic.AnsibleModule, 'run_command', side_effect=fake_run_command), \
                mock.patch.object(basic.AnsibleModule, 'warn', side_effect=self.warnings.append), \
                mock.patch.object(basic.AnsibleModule, 'exit_json', side_effect=finish(False)), \
                mock.patch.object(basic.AnsibleModule, 'fail_json', side_effect=finish(True)):
            with self.assertRaises(ModuleExit) as raised:
                scylla_cqlsh.main()
        return raised.exception

    def test_socket_login_runs_the_statements_over_the_socket(self):
        path = self.make_socket()
        self.write_yaml("maintenance_socket: %s\n" % path)

        outcome = self.run_module(dict(login='maintenance_socket', statements=["CREATE ROLE a", "DROP ROLE b;"]))

        self.assertFalse(outcome.failed)
        self.assertEqual(outcome.result['login'], 'maintenance_socket')
        self.assertEqual(outcome.result['socket'], path)
        self.assertTrue(outcome.result['changed'])
        (call,) = self.calls
        self.assertEqual(call['command'], ['cqlsh', path, '-f', call['script_path']])
        self.assertEqual(call['script'], "CREATE ROLE a;\nDROP ROLE b;\n")
        self.assertEqual(call['script_mode'], 0o600)

    def test_credentials_login_connects_over_the_network(self):
        self.write_yaml("maintenance_socket: ignore\n")

        outcome = self.run_module(dict(login='credentials', username='admin', password='s3cr%t \'#"',
                                       host='10.0.0.1', port=9142, statements=["SELECT * FROM t WHERE a = 'x y'"]))

        self.assertFalse(outcome.failed)
        self.assertNotIn('socket', outcome.result)
        (call,) = self.calls
        self.assertEqual(call['command'], ['cqlsh', '10.0.0.1', '9142', '-u', 'admin', '-p', 's3cr%t \'#"',
                                           '-f', call['script_path']])
        self.assertEqual(call['script'], "SELECT * FROM t WHERE a = 'x y';\n")

    def test_statements_stay_out_of_the_command_line(self):
        self.write_yaml("maintenance_socket: ignore\n")
        self.run_module(dict(login='credentials', username='a', password='b',
                             statements=["CREATE ROLE r WITH PASSWORD = 'hunter2'"]))
        self.assertNotIn('hunter2', ' '.join(self.calls[0]['command']))

    def test_temporary_files_are_removed(self):
        self.write_yaml("maintenance_socket: ignore\n")
        self.run_module(dict(login='credentials', username='a', password='b', statements=["SELECT 1"]))
        self.assertFalse(os.path.exists(os.path.dirname(self.calls[0]['script_path'])))

    def test_auto_uses_the_socket_when_there_is_one(self):
        path = self.make_socket()
        self.write_yaml("maintenance_socket: %s\n" % path)
        outcome = self.run_module(dict(username='a', password='b', statements=["SELECT 1"]))
        self.assertEqual(outcome.result['login'], 'maintenance_socket')
        self.assertEqual(self.warnings, [])

    def test_auto_falls_back_to_credentials_with_a_warning(self):
        self.write_yaml("maintenance_socket: ignore\n")
        outcome = self.run_module(dict(username='a', password='b', statements=["SELECT 1"]))
        self.assertEqual(outcome.result['login'], 'credentials')
        self.assertEqual(len(self.warnings), 1)
        self.assertIn("'maintenance_socket' is 'ignore'", self.warnings[0])

    def test_explicit_credentials_login_does_not_warn(self):
        self.write_yaml("maintenance_socket: ignore\n")
        self.run_module(dict(login='credentials', username='a', password='b', statements=["SELECT 1"]))
        self.assertEqual(self.warnings, [])

    def test_missing_scylla_yaml_means_defaults(self):
        outcome = self.run_module(dict(login='maintenance_socket', statements=["SELECT 1"]))
        self.assertTrue(outcome.failed)
        self.assertIn('/var/lib/scylla/cql.m', outcome.result['msg'])
        self.assertEqual(self.calls, [])

    def test_failed_cqlsh_is_reported_with_the_login_used(self):
        self.write_yaml("maintenance_socket: ignore\n")
        outcome = self.run_module(dict(login='credentials', username='a', password='b', statements=["SELECT 1"]),
                                  outcome=(2, '', 'Bad credentials\n'))
        self.assertTrue(outcome.failed)
        self.assertEqual(outcome.result['login'], 'credentials')
        self.assertEqual(outcome.result['rc'], 2)
        self.assertEqual(outcome.result['msg'], 'cqlsh exited with status 2: Bad credentials')

    def test_check_mode_runs_nothing(self):
        path = self.make_socket()
        self.write_yaml("maintenance_socket: %s\n" % path)
        outcome = self.run_module(dict(login='maintenance_socket', statements=["SELECT 1"]), check_mode=True)
        self.assertFalse(outcome.failed)
        self.assertFalse(outcome.result['changed'])
        self.assertEqual(outcome.result['login'], 'maintenance_socket')
        self.assertEqual(self.calls, [])

    def test_statements_cannot_be_empty(self):
        outcome = self.run_module(dict(login='credentials', username='a', password='b', statements=[" ", ""]))
        self.assertTrue(outcome.failed)
        self.assertEqual(self.calls, [])

    def test_username_requires_password(self):
        outcome = self.run_module(dict(username='a', statements=["SELECT 1"]))
        self.assertTrue(outcome.failed)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
