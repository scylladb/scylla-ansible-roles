# Replace dead node procedure automation

This playbook will run the replace dead node procedure.

## Prerequisites

* A scylla cluster with scylla-manager and scylla-monitoring installed.
* The inventory file must be updated as described in the Usage section below, ie.: The new node should replace the dead node in the inventory.
* It's necessary to have files with the same parameters used when the cluster was created, as described in the Parameters section.
* It's very important to have `start_scylla_service` set to `false`. The replace will not work otherwise.

## Usage:

1. Add the new node to the inventory:

Old inventory:
```old inventory
  [scylla]
  10.0.0.1
  10.0.0.2  <-- dead node to be replaced
  10.0.0.3
```

New inventory:
```new inventory
  [scylla]
  10.0.0.1
  10.0.0.4  <-- new node
  10.0.0.3
```

2. Run `ansible-playbook -i inventory.ini -e "@nodes_params.yml" -e "@monitor_params.yml" -e "replaced_node=10.0.0.2" -e "replaced_node_broadcast_address=10.0.0.2" -e "new_node=10.0.0.4" replace_node.yml`

## Steps:

1. Validate that the node being replaced is down
2. Block the broadcast address of the replaced node via iptables in all the other nodes to prevent it from trying to join the cluster again
3. Check if all the other nodes are up
4. Install Scylla in the new node
5. Set `replace_node_first_boot`/`replace_address_first_boot` in the `scylla.yaml` of the new node
6. Start `scylla-server`
7. Remove `replace_node_first_boot`/`replace_address_first_boot` from the `scylla.yaml` of the new node
8. Start `scylla-manager-agent`
9. Update Scylla-Monitoring
10. If RBNO is disabled, repair the new node

## Parameters:

This playbook uses the node role to install and configure Scylla in the new node, so the same parameters
used when the cluster was created should also be passed to the `replace_node.yml` playbook.
In the `Usage` section of this README, we use `nodes_params.yml` and `monitor_params.yml` files to represent such parameters.

Besides the vars from the node role, this playbook has the following mandatory parameters: `replaced_node`, `replaced_node_broadcast_address` and `new_node`.
These and the other available parameters are listed and described in `vars/main.yml`.
