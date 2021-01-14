# run_major_compaction playbook

The playbook will iterate over the Scylla nodes in the inventory and run `nodetool compact` with the following options:

- Full compaction (all keyspaces and tables)
- Keyspace compaction (all tables in a keyspace)
- Specific tables (specify a list of tables from a keyspace to compact)

## Node execution parallellism
Use limits (-l) to limit the nodes where the compactions will be run. See https://docs.ansible.com/ansible/latest/user_guide/intro_patterns.html#patterns-and-ansible-playbook-flags for additional information.

The playbook defaults to running compactions or a given set of nodes (or all nodes) sequentially one node at a time.

- To run on multiple nodes at a time, run with `-e "node_batch_size=N"`.
- To run on all nodes use `-e "node_batch_size=100%"`

## Specifying the compaction targets

It is easiest to specify the target inside the playbook's `vars`:

```
- name: Run major compaction
  hosts: scylla
  gather_facts: false
  serial: "{{ node_batch_size|default(1) }}"
  vars:
    # compact all the keyspaces and tables on configured nodes
    compact: all

    # compact all tables in keyspace "ks1"
    compact:
      keyspace: ks1

    # compact tables "tb3" and "tb1" in keyspace "ks2"
    compact:
      keyspace: ks2
      tables:
        - tb3
        - tb1
```

