# Scylla Ansible Roles

This repo contains the Ansible roles and example playbooks used for deploiying and maintaining Scylla clusters.
The roles produce some outputs that can be used with the other roles, running all 3 in tandem is recommended, but not required. 



## Roles:

### ansible-scylla-node role

This role will deploy Scylla on the provided set of roles. Please see the role's README and defaults/main.yml for variable settings.
The inventory also has to be configured properly for this role, specifically the `[scylla]` group members, if using the GPFS snitch much have `dc` and `rack` properties, and if using one of the public-cloud snitches they need to have `dc_suffix` set the same way. 


### ansible-scylla-manager role

This role will deploy Scylla Manager on the given host(s). If __ansible-scylla-node__ was run before with the `scylla_manager_enabled` var set to `true`, there will be a pre-generated auth token already prepared and applied to the nodes to use. Manager will be installed and connected to the Scylla cluster.


### ansible-scylla-monitoring role

This role will install Scylla Monitoring (a prometheus/grafana based, containerized monitoring stack). If the __ansible-scylla-node__ role was run previously with `generate_monitoring_config` set to `true`, there is already a scylla-servers.yaml file prepared for the stack to use, in order to connect to the existing cluster. 


### example-playbooks

Some basic playbooks showing off how the roles can be utilized, as well as some playbooks used for standard day-2 ops with Scylla
