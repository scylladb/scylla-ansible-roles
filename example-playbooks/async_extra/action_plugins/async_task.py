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

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.executor.task_result import TaskResult
from ansible.inventory.host import Host

DOCUMENTATION = r'''
---
plugin: async_task
short_description: Runs asynchronous recoverable job
description: This is a replacement for:

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
      async_wait:
        alias: blah
        retries: 100
        delay: 5

author:
- Ivan Prisyazhnyy, ScyllaDB <ivan@scylladb.com>
'''

EXAMPLES = r'''
---
- name: Async recoverable job blah
  async_task:
    shell: |
      echo Hello &&
      sleep 10
    alias: blah
    async: 1000
    retries: 100
    delay: 5
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


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        alias = self._task.args.get("alias", "")
        if not alias:
            raise AnsibleActionFail("alias is required")

        if 'async' not in self._task.args:
            raise AnsibleActionFail("async is required")

        running = self.find_running_task(alias, task_vars)
        if is_failed(running):
            result.update(running)
            return result

        if running['started'] != 1:
            obj = self.run_async_task(task_vars)
            if is_failed(result):
                result.update(obj)
                return result

            obj = self.reg_async_task(obj['ansible_job_id'], alias, task_vars)
            if is_failed(obj):
                result.update(obj)
                return result
        else:
            task = self._task.copy()
            task.name = self._task.name + " - execute async job"
            self.v2_on_result(Host(), task, {'skipped': 1})
            task.name = self._task.name + " - register async job"
            self.v2_on_result(Host(), task, {'skipped': 1})

        retries = int(self._task.args.get('retries', 0))
        delay = int(self._task.args.get('delay', 0))
        poll = int(self._task.args.get('poll', 0))

        if retries or delay:
            if poll:
                raise AnsibleActionFail("poll is not supported together with retries or delay")

            result.update(self.wait_async_task(
                alias=alias,
                cleanup=self._task.args.get('cleanup', True),
                retries=retries,
                delay=delay,
                vars=task_vars
            ))
        elif poll:
            raise AnsibleActionFail("poll is not supported yet")

        return result

    def find_running_task(self, alias, vars):
        task = self._task.copy()
        task.name = self._task.name + " - lookup existing job"
        task.args = {'alias': alias}
        task._ds = {
            "name": task.name,
            "async_status_id": {
                "alias": alias
            }
        }

        handler = self._shared_loader_obj.action_loader.get('async_status_id',
                                                            task=task,
                                                            connection=self._connection,
                                                            play_context=self._play_context,
                                                            loader=self._loader,
                                                            templar=self._templar,
                                                            shared_loader_obj=self._shared_loader_obj)
        result = handler.run(task_vars=vars)
        return self.v2_on_result(Host(), task, result)

    def run_async_task(self, vars):
        task = self._task.copy()
        task.name = self._task.name + " - execute async job"

        task.async_val = int(task.args['async'])
        task.args.pop('async')

        if 'poll' in task.args:
            task.poll = int(task.args['poll'])
            task.args.pop('poll')

        if 'shell' in task.args:
            task.args['_raw_params'] = task.args['shell']
            # Shell module is implemented via command with a special arg
            task.args['_uses_shell'] = True
            task.args.pop('shell')

        allowed = ('_raw_params', '_uses_shell', 'argv', 'chdir', 'executable', 'creates', 'removes', 'warn', 'stdin',
                   'stdin_add_newline', 'strip_empty_ends')

        for item in list(task.args.keys()):
            if item not in allowed:
                task.args.pop(item)

        handler = self._shared_loader_obj.action_loader.get('ansible.legacy.command',
                                                            task=task,
                                                            connection=self._connection,
                                                            play_context=self._play_context,
                                                            loader=self._loader,
                                                            templar=self._templar,
                                                            shared_loader_obj=self._shared_loader_obj)
        result = handler.run(task_vars=vars)
        return self.v2_on_result(Host(), task, result)

    def reg_async_task(self, jid, alias, vars):
        task = self._task.copy()
        task.name = self._task.name + " - register async job"
        task.args = {'alias': alias, 'jid': jid}
        task._ds = {
            "name": task.name,
            "async_alias": {
                "alias": alias,
                "jid": jid
            }
        }

        handler = self._shared_loader_obj.action_loader.get('async_alias',
                                                            task=task,
                                                            connection=self._connection,
                                                            play_context=self._play_context,
                                                            loader=self._loader,
                                                            templar=self._templar,
                                                            shared_loader_obj=self._shared_loader_obj)
        result = handler.run(task_vars=vars)
        return self.v2_on_result(Host(), task, result)

    def wait_async_task(self, alias, cleanup, retries, delay, vars):
        task = self._task.copy()
        task.name = self._task.name + " - wait async job"
        task.args = {
            'alias': alias,
            'cleanup': cleanup,
            'retries': retries,
            'delay': delay
        }
        task._ds = {
            "name": task.name,
            "async_wait": task.args.copy()
        }
        task.retries = retries
        task.delay = delay

        handler = self._shared_loader_obj.action_loader.get('async_wait',
                                                            task=task,
                                                            connection=self._connection,
                                                            play_context=self._play_context,
                                                            loader=self._loader,
                                                            templar=self._templar,
                                                            shared_loader_obj=self._shared_loader_obj)
        result = handler.run(task_vars=vars)
        return self.v2_on_result(Host(), task, result)

    def v2_on_result(self, host, task, result):
        handler = self._shared_loader_obj.callback_loader.get('default')
        handler._display = self._display
        handler.display_ok_hosts = True
        handler.display_failed_stderr = True
        handler.display_skipped_hosts = True

        payload = TaskResult(host=host, task=task, return_data=result, task_fields=self._task.dump_attrs())

        if 'failed' in result and result['failed']:
            handler.set_option('show_task_path_on_failure', True)
            # do nothing, because the failed result will be passed to the parent task
            # handler.v2_runner_on_failed(payload)
        elif 'skipped' in result and result['skipped']:
            handler.v2_runner_on_skipped(payload)
        else:
            handler.v2_runner_on_ok(payload)

        return result


def is_failed(result):
    return 'failed' in result and result['failed']

