# Use ideal token ring for empty non initialized cluster

This is an ansible playbook that lets you assign ideal token ring to a known size cluster

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
