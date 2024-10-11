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

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.utils.vars import merge_hash


class ActionModule(ActionBase):

    _VALID_ARGS = frozenset(('jid', 'alias', 'mode'))

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        jid = ""
        if "jid" in self._task.args:
            jid = self._task.args["jid"]

        alias = ""
        if "alias" in self._task.args:
            alias = self._task.args["alias"]

        mode = self._task.args.get("mode", "status")

        if not jid and not alias:
            raise AnsibleError("jid or alias is required")

        env_async_dir = [e for e in self._task.environment if
                         "ANSIBLE_ASYNC_DIR" in e]
        if len(env_async_dir) > 0:
            # for backwards compatibility we need to get the dir from
            # ANSIBLE_ASYNC_DIR that is defined in the environment. This is
            # deprecated and will be removed in favour of shell options
            async_dir = env_async_dir[0]['ANSIBLE_ASYNC_DIR']

            msg = "Setting the async dir from the environment keyword " \
                  "ANSIBLE_ASYNC_DIR is deprecated. Set the async_dir " \
                  "shell option instead"
            self._display.deprecated(msg, "2.12", collection_name='ansible.builtin')
        else:
            # inject the async directory based on the shell option into the
            # module args
            async_dir = self.get_shell_option('async_dir', default="~/.ansible_async")

        module_args = dict(mode=mode, _async_dir=async_dir)
        if jid:
            module_args['jid'] = jid
        if alias:
            module_args['alias'] = alias

        status = self._execute_module(module_name='async_status_id', task_vars=task_vars,
                                      module_args=module_args)
        results = merge_hash(results, status)

        return results
