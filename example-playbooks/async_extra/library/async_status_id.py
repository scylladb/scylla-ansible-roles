#!/usr/bin/env python3
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


class Result:
    def __init__(self, jid, alias):
        self.ansible_job_id = jid
        self.ansible_job_alias = alias
        self.started = 0
        self.finished = 0
        self.log_path = ""


def main():
    module = AnsibleModule(argument_spec=dict(
        jid=dict(type='str', required=True),
        alias=dict(type='str', required=True),
        mode=dict(type='str', default='status', choices=['cleanup', 'status']),
        # passed in from the async_status action plugin
        _async_dir=dict(type='path', required=True),
    ))

    mode = module.params['mode']
    jid = module.params['jid']
    alias = module.params['alias']
    async_dir = module.params['_async_dir']

    # setup logging directory
    logdir = os.path.expanduser(async_dir)
    result = Result(jid, alias)

    if jid:
        log_path = os.path.join(logdir, jid)
        result.log_path = log_path
        if not os.path.exists(log_path):
            module.fail_json(msg="could not find job", **result.__dict__)
    elif alias:
        alias_path = os.path.join(logdir, "jid_" + alias)
        log_path = alias_path
        result.log_path = log_path
        if not os.path.exists(log_path):
            module.exit_json(**result.__dict__)
        # follow symlink
        result.log_path = os.readlink(log_path)
        jid = os.path.basename(result.log_path)
        result.ansible_job_id = jid
        if not os.path.exists(log_path):
            module.fail_json(msg="could not find job", **result.__dict__)
    else:
        module.fail_json(msg="could not find job", **result.__dict__)

    if mode == 'cleanup':
        os.unlink(log_path)
        module.exit_json(erased=log_path, **result.__dict__)

    # NOT in cleanup mode, assume regular status mode
    # no remote kill mode currently exists, but probably should
    # consider log_path + ".pid" file and also unlink that above
    result.started = 1

    data = None
    try:
        with open(log_path) as f:
            data = json.loads(f.read())
    except Exception:
        if not data:
            # file not written yet?  That means it is running
            module.exit_json(**result.__dict__)
        else:
            module.fail_json(msg="Could not parse job output: %s" % data, **result.__dict__)

    if 'started' not in data:
        result.finished = 1
    elif 'finished' not in data:
        result.finished = 0

    # merge
    data = {**data, **result.__dict__}

    # Fix error: TypeError: exit_json() keywords must be strings
    data = dict([(to_native(k), v) for k, v in iteritems(data)])

    module.exit_json(**data)


if __name__ == '__main__':
    main()
