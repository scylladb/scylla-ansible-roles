# Replace dead node procedure automation

This playbook will run the replace dead node procedure.

### Steps:

1. Check if the node is a seed, if it is stop, seeds need to be demoted first.
2. Apply the ansible-scylla-node role to the new node, reusing all the parameters from the existing cluster. Skip starting the scylla-server service
3. Start the services
4. Clean out the replace_address_first_boot record from scylla.yaml
5. Run `nodetool repair -pr`

## Usage:

1. Reuse the existing set of parameters from the ansble-scylla-node run for the existing cluster. In this case I copy a previously created file called `nodes_params.yml` to `replace_params.yml`.
2. Add the new node to the inventory:

```ini
  [scylla]
  10.0.0.1
  10.0.0.2
  10.0.0.3  <-- dead node to be replaced

  [new_node]
  10.0.0.4
```

3. Edit the `replace_params.yml` file, look for (or add) the `scylla_yaml_params` variable:

```yaml
scylla_yaml_params:
  authorizer: CassandraAuthorizer
  authenticator: PasswordAuthenticator
  internode_compression: all
  #Add this line:
  replace_address_first_boot: "{{ replaced_node }}"

```

4. Run `ansible-playbook -i inventory.ini -e @replace_params.yml replace_node.yml
5. Update the inventory `[scylla]` listing with the new node's address, remove the old address.