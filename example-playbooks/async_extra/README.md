Ansible asynchronous named jobs
===

The set of modules and plugins offers the mechanism to organize
named jobs on top of the Ansible standard async architecture. It
is fully compatible with Ansible native async wrapper and status.

Architecture
===

Ansible native
---

Ansible async uses the following folder by default for storing
jobs states:

- `~/.ansible_async`

The jobs usually have ID called `JID = random hex + '.' + parent id (pid)`.
A job state is kept in files such as:

    ~/.ansible_async/959330701595.43243

and contain json objects. A json looks like the following for the
finished jobs:

    {
        "cmd": "echo Hello &&\nsleep 10\n",
        "stdout": "Hello",
        "stderr": "",
        "rc": 0,
        "start": "2021-05-14 18:00:36.164859",
        "end": "2021-05-14 18:00:46.169185",
        "delta": "0:00:10.004326",
        "changed": true,
        "invocation": {
            "module_args": {
                "_raw_params": "echo Hello &&\nsleep 10\n",
                "_uses_shell": true,
                "warn": false,
                "stdin_add_newline": true,
                "strip_empty_ends": true,
                "argv": null,
                "chdir": null,
                "executable": null,
                "creates": null,
                "removes": null,
                "stdin": null
            }
        }
    }

and the following for just started ones:

    {"started": 1, "finished": 0, "ansible_job_id": "454921468804.48399"}

While the wrapper is working it keeps `${jid}.tmp` file near the state file.

These modules
---

We define a job name (alias) as a soft-link to the job state:

    ${jid}.jid_${alias} -> ${jid}

General algorithm is:

1. Find job by name
2. If (1) is false: execute new async job
3. If (1) is false: register job alias (name)
4. Wait for job to finish
5. Cleanup finished job alias if needed

Job states
---

- Started: started == 1
- Finished: finished == 1 or no started field in the job's state
- Killed: killed == True
- Started but pid_missing == True and unfinished

Ansible addons architecture
===

            Caller site    |  Remote
                           |
    Task -> Action plugin --> Module

Action plugins usually verify arguments, prepare execution context,
and call other actions and modules. Actions execute on the caller site.
If the action plugin is missing a task can directly call a module.
A module has JSON API.

For example:

    - async_status_id: alias="blah"

Calls action plugin `action_plugin/async_status_id.py` that in its turn
calls a module `library/async_status_id.py`.

async_status_id
===

This component gets the status of an asynchronous task. It can find
a task's job by its name (alias).

Features:

- lookup by job name (alias)
- killed jobs support (killed)
- always checks that the wrapper is alive and running (pid_missing)
- always outputs started and finished fields
- default `cleanup` mode cleanups only an alias if the job was specified
  by its name. if it was specified by a jid it deletes the whole state.
- `full_cleanup` deletes job's state and all related links

Quick start
---

Simplest usage:

    - name: Find out if the task exists
      async_status_id: alias="blah"
      register: job_result

Example 1
---

Possible implementation of the named recoverable jobs with this component alone:

    - name: Find if the task exists
      async_status_id: alias="blah"
      register: job_result
    - name: Execute an async job Blah
      shell: |
        echo Hello &&
        sleep 60
      async: 1000
      poll: 0
      register: async_task_obj
      when: not job_result.started
    - name: Register task alias
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

This implementation do not handle overwrite of the aliases from other jobs
at the step of registering a job alias. Neither it handles killed jobs.

Example 2
---

The same as Example 1 but with `async_alias`:

    - name: Find if the task exists
      async_status_id: alias="blah"
      register: job_result
    - name: Execute an async job Blah
      shell: |
        echo Hello &&
        sleep 60
      async: 1000
      poll: 0
      register: async_task_obj
      when: not job_result.started
    - name: Register task alias
      async_alias: job=async_task_obj alias=blah
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

Example 3
---

An example shows an implementation of simple wait for an async job.

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
   
Debug
---

Actions may be executed via the `ansible-playground` with:

    $ ansible-playbook -vvvv ./async_status_id_recoverable.yml

Additional debug output can be enabled via:

    $ ANSIBLE_DEBUG=true ansible-playbook -vvvv ./async_status_id_recoverable.yml

Module alone can be tested with:

    $ ./test_async_status_id.sh blah

or

    $ echo "{ \"ANSIBLE_MODULE_ARGS\": { \"alias\": \"$1\", \"_async_dir\": \"$HOME/.ansible_async\" } }" | PYTHONPATH=library python -m async_status_id

async_alias
===

Registers job alias by its id.

Is equivalent to:

    - file:
        src: "{{ async_task_obj.results_file }}"
        dest: "{{ async_task_obj.results_file | dirname }}/jid_{{alias}}"
        state: link

Simple example:

    - async_alias: job=async_task_obj alias=blah
      when: not job_result.started