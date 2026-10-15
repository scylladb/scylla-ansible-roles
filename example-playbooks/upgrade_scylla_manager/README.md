# Upgrade Scylla Manager

Upgrades the Scylla Manager server and `scylla-manager-agent` on all Scylla nodes.

## Prerequisites

* Inventory groups `scylla-manager` and `scylla`.
* The same variables you used to deploy the cluster, in the same params files.

## Update Params Files

Point the Manager repo variables at the target series. Set them in both the manager params file (`group_vars/scylla-manager.yml`, read by [ansible-scylla-manager](https://github.com/scylladb/scylla-ansible-roles/blob/master/ansible-scylla-manager/defaults/main.yml)) and the node params file (`group_vars/scylla.yml`, read by [ansible-scylla-node](https://github.com/scylladb/scylla-ansible-roles/blob/master/ansible-scylla-node/defaults/main.yml) for the agents):

```yaml
scylla_manager_deb_repo_url: "https://downloads.scylladb.com/deb/ubuntu/scylladb-manager-3.11.list"
scylla_manager_rpm_repo_url: "https://downloads.scylladb.com/rpm/centos/scylladb-manager-3.11.repo"
```

## Trigger Upgrade

Recommended: limit `ansible-scylla-node` to its manager-agent install tasks with `--tags manager_agent_upgrade`. The other plays are tagged `always`, so they still run:

```bash
ANSIBLE_ROLES_PATH=$PATH_TO_YOUR_CLONED_REPO ansible-playbook -i inventory.ini --tags manager_agent_upgrade $PATH_TO_YOUR_CLONED_REPO/example-playbooks/upgrade_scylla_manager/upgrade_scylla_manager.yml
```

Without `--tags`, the playbook runs `ansible-scylla-node` in full on every `scylla` host while Scylla Manager and its agents are stopped. That is a complete node-role converge, not just a Manager upgrade, so only do it if you intend that.

## Suspend and Resume

The playbook runs `sctool suspend` on every cluster in `scylla_clusters` before the upgrade and `sctool resume` after it. Two things to expect:

* A backup or repair that is running when the upgrade starts is stopped by the suspend. The resume runs with `--start-tasks` and `--start-tasks-missed-activation`, so it is started again right after the upgrade, together with any task whose scheduled activation fell inside the suspended window, instead of waiting for the next activation. This matters most after a failed run, when the cluster stays suspended until the rerun.
* A cluster that was already suspended before the run is resumed at the end too. Suspend it again afterwards if it needs to stay suspended.

## If the Playbook Fails

The Manager tasks are suspended and Scylla Manager and the agents are stopped early in the playbook. If a play fails after that point, the tasks stay suspended and the services that have not been started again yet stay stopped. Rerun the playbook end to end: suspending is skipped when `scylla-manager` is not active, suspending an already suspended cluster does nothing, and the roles converge, so a rerun is safe. Don't start the services by hand unless you have confirmed the install is consistent.
