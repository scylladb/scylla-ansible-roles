# Manage users

This is an ansible playbook that allows the creation of cql users and deletes the default cassandra user.

## Prerequisites

* A scylla cluster with authentication enabled.

## Parameters / Default Behavior

* `scylla_nic`: The network interface being used by scylla.
* `scylla_nic_ipv4_addr`: IPv4 address for the network interface being used by scylla.
* `delete_cassandra_user`: A boolean indicating if the default cassandra user must be deleted or not.
* `scylla_admin_username`: The username of the superuser which will be replacing the default cassandra user.
* `users`: A map with the users (besides `scylla_admin_username`) which are going to be added.
           Every user is a map containing the following entries:
    * `superuser` -> a boolean indicating if the new user is a superuser
    * `permissions` (optional) -> A list with the permissions. Every permission is represented by a list
                                  with 2 positions, where the first position is the name of the permission
                                  and the second position is the resource for which this permission is being added.
                                  A list with the available permissions can be found in {https://docs.scylladb.com/stable/operating-scylla/security/authorization.html#permissions}.

In order to connect via cqlsh and update the credentials, this playbook will try to get the `rpc_address` on scylla.yaml.
If this value is not set, then it'll be assumed that localhost is being used, since this is the default value on scylla and the
playbook will try to find out the IP address by getting the IPv4 for the default network interface.
If you want, you can override the variables `scylla_nic` and `scylla_nic_ipv4_addr` to choose the nic and ipv4 address which you'd like
the playbook to use in case rpc is not set.
If `rpc_address` is set to 0.0.0.0, this playbook will use `broadcast_rpc_address`.

By default, this playbook will create the users `scylla_admin` (superuser), `scylla_cql_monitor` and `customer_admin`.
Their default permissions are listed in `vars/main.yml`.
You can override the variable `users` in order to add a different list of users with a different set of permissions.

Every user defined in this playbook must be also defined in the inventory file under the section `[cql_credentials]` followed by its password.
E.g.:
```
[cql_credentials]
scylla_admin=password1
scylla_cql_monitor=password2
customer_admin=password3
```

## Allowed operations

* Addition of users
* Addition of permissions for any user (Removing permissions isn't supported)
* Changing password for any user except `scylla_admin`

## Inventory

Put public IP addresses of all nodes under the section `[scylla]` in the inventory.

## Running

Run the playbook:

```
ansible-playbook -i inventory.ini manage_users.yaml [-e "@users.yml"]
```
