#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 ScyllaDB
#

#
# This file is part of Scylla.
#
# Scylla is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Scylla is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Scylla.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, division, print_function

import json
import os
import signal

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems
from ansible.module_utils.common.text.converters import to_native

__metaclass__ = type

DOCUMENTATION = r'''
---
module: async_kill
short_description: Finds existing async job and kills it
description:
- This module gets the status of an asynchronous task.
options:
  jid:
    description:
    - Job or task identifier
    type: str
    optional: true
  alias:
    description:
    - Job alias
    type: str
    optional: true
  signal:
    SIGTERM
author:
- Ivan Prisyazhnyy, ScyllaDB <ivan@scylladb.com>
'''

EXAMPLES = r'''
---
- name: Async task
  shell: |
    echo Hello &&
    sleep 60
  async: 1000
  poll: 0
  register: async_task_obj

- name: Kill the job by id
  async_kill:
    jid: '{{ async_task_obj.ansible_job_id }}'
'''

RETURN = r'''
ansible_job_id:
  description: The asynchronous job id
  returned: success
  type: str
  sample: '360874038559.4169'
killed:
  description: Whether the asynchronous job was killed (C(1)) or not (C(0))
  returned: success
  type: boolean 
  sample: True
'''


def main():
    module = AnsibleModule(argument_spec=dict(
        jid=dict(type='str'),
        alias=dict(type='str'),
        signal=dict(type='int', default=signal.SIGTERM),
        # passed in from the async_status action plugin
        _async_dir=dict(type='path', required=True),
    ),
        required_one_of=[['jid', 'alias']],
        mutually_exclusive=[['jid', 'alias']]
    )

    request = Request(module)
    response = Response(request)

    t = Tracker(module, response)
    data = t.load_job_state(request.log_path)
    module.debug("current state %s" % data)
    t.update_state(data)

    if response.finished:
        module.debug("job is finished. nothing to kill.")
        module.exit_json(**response.__dict__)

    if response.killed:
        module.debug("job has been killed previously. nothing to kill.")
        module.exit_json(**response.__dict__)

    pid = t.get_jid_pid(request.jid)
    alive = [pid]
    if not t.is_pid_alive(pid):
        alive = find_pid(request.jid)
        if not alive:
            module.debug("job is unfinished and no wrapper alive. nothing to kill.")
            module.exit_json(**response.__dict__)

    # kill
    module.debug("alive pids = %s" % alive)

    data['killed'] = True
    prepare_state_update(request.log_path, data, "kill")

    for pid in alive:
        module.debug("killing group pid = %d, sig = %d" % (pid, request.signal))
        t.kill_all(pid, request.signal)

    commit_state_update(request.log_path, "kill")
    # cleanup running wrapper marker
    try_cleanup_state_update(request.log_path, "tmp")
    response.killed = True

    module.exit_json(**response.__dict__)


class Request:
    def __init__(self, module):
        self.jid = module.params.get('jid')
        self.alias = module.params.get('alias')
        self.signal = int(module.params.get('signal', signal.SIGTERM))
        self.async_dir = module.params['_async_dir']
        self.log_dir = os.path.expanduser(self.async_dir)
        self.log_path = ""
        self.alias_path = ""

        self.parse(module)

    def parse(self, module):
        if self.jid:
            self.log_path = os.path.join(self.log_dir, self.jid)
            if not os.path.exists(self.log_path):
                module.fail_json(msg="could not find job", **Response(self).__dict__)
        elif self.alias:
            self.alias_path = os.path.join(self.log_dir, "jid_" + self.alias)
            self.log_path = self.alias_path
            if not os.path.exists(self.log_path):
                module.exit_json(**Response(self).__dict__)
            # follow symlink
            self.log_path = os.readlink(self.alias_path)
            self.jid = os.path.basename(self.log_path)
            if not os.path.exists(self.log_path):
                module.fail_json(msg="could not find job", **Response(self).__dict__)
        else:
            module.fail_json(msg="could not find job", **Response(self).__dict__)


class Response:
    def __init__(self, request):
        self.ansible_job_id = request.jid
        self.ansible_job_alias = request.alias
        self.started = 0
        self.finished = 0
        self.killed = False
        self.log_path = request.log_path
        self.alias_path = request.alias_path

    def merge(self, data):
        self.__dict__ = {**self.__dict__, **data}


class Tracker:
    def __init__(self, module, response):
        self.module = module
        self.response = response

    def load_job_state(self, log_path):
        data = None
        try:
            with open(log_path) as f:
                data = json.loads(f.read())
        except Exception:
            if not data:
                # file not written yet?  That means it is running
                self.module.exit_json(**self.response.__dict__)
            else:
                self.module.fail_json(msg="Could not parse job output: %s" % data, **self.response.__dict__)

        return data

    def update_state(self, data):
        # semantics: if log file exists then the job has been started
        self.response.merge(data)
        self.response.started = 1
        if 'started' not in data:
            self.response.finished = 1
        elif 'finished' not in data:
            self.response.finished = 0

    def get_jid_pid(self, jid):
        s = str(jid).split('.')
        if len(s) != 2:
            self.module.fail_json(msg="Unexpected jid format: %s" % jid, **self.response.__dict__)
        return int(s[1])

    def is_pid_alive(self, pid):
        try:
            os.kill(pid, 0)
        except OSError as err:
            import errno

            if err.errno == errno.ESRCH:
                return False
            elif err.errno == errno.EPERM:
                self.module.fail_json(msg="No permission to signal this process: %d" % pid, **self.response.__dict__)
            else:
                self.module.fail_json(msg="Unknown error: %s" % err, **self.response.__dict__)

        return True

    def kill_all(self, gpid, sig):
        try:
            os.killpg(gpid, sig)
        except OSError as err:
            import errno

            if err.errno == errno.ESRCH:
                return False
            elif err.errno == errno.EPERM:
                self.module.fail_json(msg="No permission to signal this process: %d <- %d" % (gpid, sig), **self.response.__dict__)
            else:
                self.module.fail_json(msg="Unknown error: %s" % err, **self.response.__dict__)

        return True


# {"started": 1, "finished": 0, "ansible_job_id": "5914760398.19030"}
def prepare_state_update(log_path, state, suffix):
    tmp_job_path = log_path + "." + suffix
    jobfile = open(tmp_job_path, "w")
    jobfile.write(json.dumps(state))
    jobfile.close()


def commit_state_update(log_path, suffix):
    tmp_job_path = log_path + "." + suffix
    os.rename(tmp_job_path, log_path)


def try_cleanup_state_update(log_path, suffix):
    tmp_job_path = log_path + "." + suffix
    if os.path.isfile(tmp_job_path):
        os.remove(tmp_job_path)


def find_pid(jid):
    import subprocess

    search = "async_wrapper.py " + get_jid_id(jid)

    ps = subprocess.Popen("ps --format=pid,ppid,pgid,cmd -e | grep '%s'" % search, shell=True, stdout=subprocess.PIPE)
    output = ps.stdout.readlines()
    ps.stdout.close()
    ps.wait()

    # 1 line is grep:
    #     0 S xxxxxx     23516   17036  0  80   0 -  1761 -      12:46 pts/0    00:00:00 grep --color=auto 365913987461
    # other 2 lines:
    #     1 S xxxxxx     21099    2564  0  80   0 -  7450 -      12:31 ?        00:00:00 /usr/bin/python
    #           /home/xxxxxx/.ansible/tmp/ansible-tmp-1620901911.527596-21084-188005885689773/async_wrapper.py
    #           365913987461 3600 /home/sitano/.ansible/tmp/ansible-tmp-1620901911.527596-21084-188005885689773/
    #           AnsiballZ_command.py _
    #     1 S xxxxxx     21100   21099  0  80   0 -  7514 -      12:31 ?        00:00:00 /usr/bin/python
    #           /home/xxxxxx/.ansible/tmp/ansible-tmp-1620901911.527596-21084-188005885689773/async_wrapper.py
    #           365913987461 3600 /home/sitano/.ansible/tmp/ansible-tmp-1620901911.527596-21084-188005885689773/
    #           AnsiballZ_command.py _

    return [int(line.decode().split()[0]) for line in output if 'python' in str(line)]


def get_jid_id(jid):
    return str(jid).split('.')[0]


if __name__ == '__main__':
    main()
