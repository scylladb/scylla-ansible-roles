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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems
from ansible.module_utils.common.text.converters import to_native

__metaclass__ = type

DOCUMENTATION = r'''
---
module: async_wait_id
short_description: Finds existing async job by alias or id
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
  mode:
    description:
    - If C(status), obtain the status.
    - If C(cleanup), clean up the async job cache (by default in C(~/.ansible_async/)) for the specified job I(jid).
    type: str
    choices: [ cleanup, status ]
    default: status
seealso:
- ref: playbooks_async
  description: Detailed information on how to use asynchronous actions and polling.
author:
- Ivan Prisyazhnyy, ScyllaDB <ivan@scylladb.com>
- Vlad Zolotarov, ScyllaDB <vladz@scylladb.com>
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

- name: Wait for asynchronous job to end
  async_status_id:
    jid: '{{ async_task_obj.ansible_job_id }}'
  register: job_result
  until: job_result.finished
  retries: 100
  delay: 10
  
---
- name: Find and wait for task if it exists
  async_status_id: alias="blah"
  register: job_result
  
- name: Async job Blah
  shell: |
    echo Hello &&
    sleep 60
  async: 1000
  poll: 0
  register: async_task_obj
  when: not job_result.started
  
- name: Register task id
  file:
    src: "{{ async_task_obj.results_file }}"
    dest: "{{ async_task_obj.results_file | dirname }}/jid_blah"
    state: link
  when: not job_result.started
  
- name: Wait for task to finish
  async_status_id: alias="blah"
  register: job_result
  until: job_result.finished
  retries: 100
  delay: 5
  
- name: Cleanup
  async_status_id:
    alias: "blah"
    mode: "cleanup"

---
- name: Find and wait for task if it exists
  async_status_id: alias=blah
  register: job_result
  
- name: Async job Blah
  shell: |
    echo Hello &&
    sleep 10
  async: 1000
  poll: 0
  register: async_task_obj
  when: not job_result.started
  
- name: Register task alias
  async_alias: job=async_task_obj alias=blah
  when: not job_result.started
  
- name: Wait for task to finish
  async_status_id: alias=blah
  register: job_result
  until: job_result.finished
  retries: 100
  delay: 5
  
- name: Cleanup
  async_status_id:
    alias: "blah"
    mode: "cleanup"
'''

RETURN = r'''
ansible_job_id:
  description: The asynchronous job id
  returned: success
  type: str
  sample: '360874038559.4169'
finished:
  description: Whether the asynchronous job has finished (C(1)) or not (C(0))
  returned: success
  type: int
  sample: 1
started:
  description: Whether the asynchronous job has been started (C(1)) or not (C(0))
  returned: success
  type: int
  sample: 1
'''


def main():
    module = AnsibleModule(argument_spec=dict(
        jid=dict(type='str'),
        alias=dict(type='str'),
        mode=dict(type='str', default='status', choices=['full_cleanup', 'cleanup', 'status']),
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

    if not response.finished and not response.killed:
        pid = t.get_jid_pid(request.jid)
        if not t.is_pid_alive(pid):
            if not find_pid(request.jid):
                # recheck that the job did not finish while we were looking at the wrapper pid
                data = t.load_job_state(request.log_path)
                t.update_state(data)
                if not response.finished:
                    response.pid_missing = True
                    module.fail_json(msg="can't find alive process." +
                                         " probably async_wrapper.py wrapper unexpectedly died." +
                                         " check how " + os.path.join(request.async_dir, request.jid) + " is doing." +
                                         " if it is failed, delete the soft link (alias) to it.", **response.data())
    else:
        if request.mode == 'cleanup':
            if request.alias:
                os.unlink(request.alias_path)
            elif request.jid:
                os.unlink(request.log_path)

        if request.mode == 'full_cleanup':
            if request.alias:
                os.unlink(request.alias_path)
            os.unlink(request.log_path)

        module.exit_json(erased=request.log_path, **response.data())

    module.exit_json(**response.data())


class Request:
    def __init__(self, module):
        self.jid = module.params.get('jid')
        self.alias = module.params.get('alias')
        self.mode = module.params.get('mode', 'status')
        self.async_dir = module.params['_async_dir']
        self.log_dir = os.path.expanduser(self.async_dir)
        self.log_path = ""
        self.alias_path = ""

        self.parse(module)

    def parse(self, module):
        if self.jid:
            self.log_path = os.path.join(self.log_dir, self.jid)
            if not os.path.exists(self.log_path):
                module.fail_json(msg="could not find job", **Response(self).data())
        elif self.alias:
            self.alias_path = os.path.join(self.log_dir, "jid_" + self.alias)
            self.log_path = self.alias_path
            if not os.path.exists(self.log_path):
                module.exit_json(**Response(self).data())
            # follow symlink
            self.log_path = os.readlink(self.alias_path)
            self.jid = os.path.basename(self.log_path)
            if not os.path.exists(self.log_path):
                module.fail_json(msg="could not find job", **Response(self).data())
        else:
            module.fail_json(msg="could not find job", **Response(self).data())


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

    def data(self):
        # Fix error: TypeError: exit_json() keywords must be strings
        return dict([(to_native(k), v) for k, v in iteritems(self.__dict__)])


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
                self.module.exit_json(**self.response.data())
            else:
                self.module.fail_json(msg="Could not parse job output: %s" % data, **self.response.data())

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
            self.module.fail_json(msg="Unexpected jid format: %s" % jid, **self.response.data())
        return int(s[1])

    def is_pid_alive(self, pid):
        try:
            os.kill(pid, 0)
        except OSError as err:
            import errno

            if err.errno == errno.ESRCH:
                return False
            elif err.errno == errno.EPERM:
                self.module.fail_json(msg="No permission to signal this process: %d" % pid, **self.response.data())
            else:
                self.module.fail_json(msg="Unknown error: %s" % err, **self.response.data())

        return True


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
