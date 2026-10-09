# Upgrade Scylla Manager

Upgrades the Scylla Manager server and `scylla-manager-agent` on all Scylla nodes.

## Prerequisites

* Inventory groups `scylla-manager` and `scylla`.
* The same variables you used to deploy the cluster, in the same params files.

## Update Params Files

Point the Manager repo variables at the target series.

In the manager params file (`group_vars/scylla-manager.yml`), for [ansible-scylla-manager](https://github.com/scylladb/scylla-ansible-roles/blob/master/ansible-scylla-manager/defaults/main.yml):

```yaml
scylla_manager_deb_repo_url: "https://downloads.scylladb.com/deb/ubuntu/scylladb-manager-3.11.list"
scylla_manager_rpm_repo_url: "https://downloads.scylladb.com/rpm/centos/scylladb-manager-3.11.repo"
```

In the node params file (`group_vars/scylla.yml`), for the agents installed by [ansible-scylla-node](https://github.com/scylladb/scylla-ansible-roles/blob/master/ansible-scylla-node/defaults/main.yml):

```yaml
scylla_manager_deb_repo_url: "https://downloads.scylladb.com/deb/ubuntu/scylladb-manager-3.11.list"
scylla_manager_rpm_repo_url: "https://downloads.scylladb.com/rpm/centos/scylladb-manager-3.11.repo"
```

## Trigger Upgrade

```bash
ANSIBLE_ROLES_PATH=$PATH_TO_YOUR_CLONED_REPO ansible-playbook -i inventory.ini $PATH_TO_YOUR_CLONED_REPO/example-playbooks/upgrade_scylla_manager/upgrade_scylla_manager.yml
```

This runs `ansible-scylla-node` in full. To only upgrade the manager agent and skip the rest of that role, add `--tags manager_agent_upgrade`; the other plays are tagged `always`, so they still run:

```bash
ANSIBLE_ROLES_PATH=$PATH_TO_YOUR_CLONED_REPO ansible-playbook -i inventory.ini --tags manager_agent_upgrade $PATH_TO_YOUR_CLONED_REPO/example-playbooks/upgrade_scylla_manager/upgrade_scylla_manager.yml
```
