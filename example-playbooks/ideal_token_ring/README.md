# Use ideal token ring for empty non initialized cluster

This is an ansible playbook that lets you assign ideal token ring to a known size cluster

## Restrictions and setting expectations

* If you invoked a script using an inventory file you should use a
  NetworkTopologyStrategy and EverywhereStrategy across the board for
  distributed keyspaces.
* If you invoked a script by giving a total number of nodes then you
  should use SimpleStrategy and EverywhereStrategy across the board
  for distributed keyspaces.

Ignoring rules above may cause a severe data distribution imbalance
especially in a multi-DC case.

This playbook uses the inventory file, so first rule/restriction has to be used.

## Prerequisites

1. New cluster which is not initialized (its inventory.ini)
2. Ideal initial token python ring scripts

## Parameters

All restore parameters shall be put to `vars.yaml` file.
Copy `vars.yaml.example` as `vars.yaml` and change parameters to match your clusters.

## Inventory

Classic inventory used for provisioning nodes using scylla ansible role

## Running

Rut the playbook:

```bash
ansible-playbook -i inventory.ini scylla -e @vars.yaml ideal_token_ring.yaml
```
