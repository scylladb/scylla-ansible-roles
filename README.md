# Scylla Ansible Roles

This repo contains the Ansible roles and example playbooks used for deploiying and maintaining Scylla clusters.
The roles produce some outputs that can be used with the other roles, running all 3 in tandem is recommended, but not required. 

For detailed documentation of each role and some of the example playbooks, please see the Wiki: https://github.com/scylladb/scylla-ansible-roles/wiki

Discussion on Slack: https://scylladb-users.slack.com/archives/C01KV03RTEV


## Roles:

### ansible-scylla-node role

This role will deploy Scylla on the provided set of roles. Please see the role's README and defaults/main.yml for variable settings.
The inventory also has to be configured properly for this role, specifically the `[scylla]` group members, if using the GPFS snitch much have `dc` and `rack` properties, and if using one of the public-cloud snitches they need to have `dc_suffix` set the same way. 

[Manual](https://github.com/scylladb/scylla-ansible-roles/wiki/ansible-scylla-node:-Deploying-a-Scylla-cluster)

### ansible-scylla-manager role

This role will deploy Scylla Manager on the given host(s). If __ansible-scylla-node__ was run before with the `scylla_manager_enabled` var set to `true`, there will be a pre-generated auth token already prepared and applied to the nodes to use. Manager will be installed and connected to the Scylla cluster.

[Manual](https://github.com/scylladb/scylla-ansible-roles/wiki/ansible-scylla-manager:-Deploying-Scylla-Manager-and-connecting-it-to-a-cluster)

### ansible-scylla-monitoring role

This role will install Scylla Monitoring (a prometheus/grafana based, containerized monitoring stack). If the __ansible-scylla-node__ role was run previously with `generate_monitoring_config` set to `true`, there is already a scylla-servers.yaml file prepared for the stack to use, in order to connect to the existing cluster. 

[Manual](https://github.com/scylladb/scylla-ansible-roles/wiki/Deploying-Scylla-Monitoring-and-connecting-it-to-a-Scylla-Cluster)

### ansible-scylla-loader role

This role will prepare a host to run a stress load against a Scylla cluster.
The following components get installed:

- Scylla Java driver
- Scylla Python driver
- cassandra-stress (in $PATH)
- tlp-stress (in $PATH)
- YCSB (in /home/ANSIBLE_USER/ycsb/VERSION)


### example-playbooks

Some basic playbooks showing off how the roles can be utilized, as well as some playbooks used for standard day-2 ops with Scylla

[Rolling restart automation](https://github.com/scylladb/scylla-ansible-roles/wiki/Rolling-restart-automation)
