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

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import time
import json

from ansible import constants as C
from ansible.errors import AnsibleConnectionFailure, AnsibleActionFail, AnsibleActionSkip
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.module_utils.six import PY3
from ansible.module_utils.six.moves import xrange
from ansible.parsing.ajson import AnsibleJSONEncoder
from ansible.plugins.action import ActionBase
from ansible.vars.clean import strip_internal_keys, module_response_deepcopy

if PY3:
    # OrderedDict is needed for a backwards compat shim on Python3.x only
    # https://github.com/ansible/ansible/pull/49512
    from collections import OrderedDict
else:
    OrderedDict = None


class TaskTimeoutError(BaseException):
    pass


DOCUMENTATION = r'''
---
plugin: async_wait 
short_description: Awaits for a job to finish
notes:
- By default cleanups the job alias after itself.
author:
- Ivan Prisyazhnyy, ScyllaDB <ivan@scylladb.com>
- Vlad Zolotarov, ScyllaDB <vladz@scylladb.com>
'''


class ActionModule(ActionBase):
    _VALID_ARGS = frozenset(['jid', 'alias', 'job', 'cleanup', 'retries', 'delay'])

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        jid = self._task.args.get("jid", "")
        alias = self._task.args.get("alias", "")
        job = self._task.args.get("job", "")
        retries = int(self._task.args.get("retries", 1))
        delay = int(self._task.args.get("delay", 0))
        cleanup = boolean(self._task.args.get("cleanup", True))

        if not jid and not alias and not job:
            raise AnsibleActionFail("one of [jid, alias, job] is required")

        if not retries:
            raise AnsibleActionFail("retries is required")

        if not delay:
            raise AnsibleActionFail("delay is required")

        if retries <= 0:
            retries = 1

        if delay < 0:
            delay = 1

        if job:
            if job not in task_vars['vars']:
                raise AnsibleActionFail("no job among facts")
            job = task_vars['vars'][job]
            if "ansible_job_id" not in job:
                raise AnsibleActionFail("job does not contain results file")
            jid = job["ansible_job_id"]

        if not jid and not alias:
            raise AnsibleActionFail("jid or alias is required")

        # wait
        wait_task = self._task.copy()
        wait_task.args = dict(mode="status")
        if alias:
            wait_task.args["alias"] = alias
        if jid:
            wait_task.args["jid"] = jid

        # wait_task.retries copied from self._task
        # wait_task.delay copied from self._task

        def wait_until(x):
            if not is_started(x):
                raise AnsibleActionFail(f"job execution failed: {x}")
            return is_finished(x) or is_failed(x) or is_killed(x)

        wait_action = self._shared_loader_obj.action_loader.get('async_status_id',
                                                                task=wait_task,
                                                                connection=self._connection,
                                                                play_context=self._play_context,
                                                                loader=self._loader,
                                                                templar=self._templar,
                                                                shared_loader_obj=self._shared_loader_obj)
        result.update(self.retry(action=wait_action, vars=task_vars,
                                 retries=retries, delay=delay,
                                 until=lambda x: wait_until(x)))

        # cleanup if tasks succeeded or if it failed and 'cleanup' was requested
        if (is_finished(result) and not is_failed(result)) or ((is_finished(result) or is_killed(result)) and cleanup):
            cleanup_task = self._task.copy()
            cleanup_task.retries = 0
            cleanup_task.delay = 0
            cleanup_task.args = dict(mode="cleanup")
            if alias:
                cleanup_task.args["alias"] = alias
            if jid:
                cleanup_task.args["jid"] = jid
            self._shared_loader_obj.action_loader.get('async_status_id',
                                                      task=cleanup_task,
                                                      connection=self._connection,
                                                      play_context=self._play_context,
                                                      loader=self._loader,
                                                      templar=self._templar,
                                                      shared_loader_obj=self._shared_loader_obj) \
                .run(task_vars=task_vars)
            result['cleanup'] = True

        return result

    # copied from ansible
    def _dump_results(self, result, indent=None, sort_keys=True, keep_invocation=False):
        if not indent and (result.get('_ansible_verbose_always') or self._display.verbosity > 2):
            indent = 4

        # All result keys stating with _ansible_ are internal, so remove them from the result before we output anything.
        abridged_result = strip_internal_keys(module_response_deepcopy(result))

        # remove invocation unless specifically wanting it
        if not keep_invocation and self._display.verbosity < 3 and 'invocation' in result:
            del abridged_result['invocation']

        # remove diff information from screen output
        if self._display.verbosity < 3 and 'diff' in result:
            del abridged_result['diff']

        # remove exception from screen output
        if 'exception' in abridged_result:
            del abridged_result['exception']

        try:
            jsonified_results = json.dumps(abridged_result, cls=AnsibleJSONEncoder, indent=indent, ensure_ascii=False,
                                           sort_keys=sort_keys)
        except TypeError:
            # Python3 bug: throws an exception when keys are non-homogenous types:
            # https://bugs.python.org/issue25457
            # sort into an OrderedDict and then json.dumps() that instead
            if not OrderedDict:
                raise
            jsonified_results = json.dumps(OrderedDict(sorted(abridged_result.items(), key=to_text)),
                                           cls=AnsibleJSONEncoder, indent=indent,
                                           ensure_ascii=False, sort_keys=False)
        return jsonified_results

    # copied from ansible
    def _run_is_verbose(self, result, verbosity=0):
        return ((self._display.verbosity > verbosity or result.get('_ansible_verbose_always', False) is True)
                and result.get('_ansible_verbose_override', False) is False)

    # copied from ansible
    def v2_runner_retry(self, result):
        task_name = self._task.name
        msg = "FAILED - RETRYING: %s (%d retries left)." % (task_name, result['retries'] - result['attempts'])
        if self._run_is_verbose(result, verbosity=2):
            msg += "Result was: %s" % self._dump_results(result)
        self._display.display(msg, color=C.COLOR_DEBUG)

    # derived from ansible
    def retry(self, action, vars, retries, delay, until):
        self._display.debug("starting attempt loop")
        result = None
        for attempt in xrange(1, retries + 1):
            self._display.debug("running the action")
            try:
                result = action.run(task_vars=vars)
            except AnsibleActionSkip as e:
                return dict(skipped=True, msg=to_text(e))
            except AnsibleActionFail as e:
                return dict(failed=True, msg=to_text(e))
            except AnsibleConnectionFailure as e:
                return dict(unreachable=True, msg=to_text(e))
            except TaskTimeoutError as e:
                msg = 'The %s action failed to execute in the expected time frame (%d) and was terminated' % (
                    self._task.action, self._task.timeout)
                return dict(failed=True, msg=msg)
            self._display.debug("action run complete")

            # set the failed property if it was missing.
            if 'failed' not in result:
                # rc is here for backwards compatibility and modules that use it instead of 'failed'
                if 'rc' in result and result['rc'] not in [0, "0"]:
                    result['failed'] = True
                else:
                    result['failed'] = False

            # Make attempts and retries available early to allow their use in changed/failed_when
            result['attempts'] = attempt

            # set the changed property if it was missing.
            if 'changed' not in result:
                result['changed'] = False

            if retries > 1:
                if until(result):
                    break
                else:
                    # no conditional check, or it failed, so sleep for the specified time
                    if attempt < retries:
                        result['_ansible_retry'] = True
                        result['retries'] = retries
                        self._display.debug('Retrying task, attempt %d of %d' % (attempt, retries))
                        self.v2_runner_retry(result)
                        time.sleep(delay)
        else:
            if retries > 1:
                # we ran out of attempts, so mark the result as failed
                result['failed'] = True
                result['attempts'] = retries
                result['msg'] = "Ran out of attempts."

        if not until(result):
            result['failed'] = True
            result['msg'] = "Job did not finish."

        return result


def is_started(result):
    return result.get('started', 0)

def is_finished(result):
    return result.get('finished', 0)

def is_failed(result):
    return result.get('failed', False)

def is_killed(result):
    return result.get('killed', False)



