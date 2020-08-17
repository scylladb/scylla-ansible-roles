Role Name
=========

A role to deploy Scylla Manager and connect it to Scylla clusters

Requirements
------------

  Roles:
    - ansible-scylla-node

Role Variables
--------------

The variables are heavily commented in `defaults/main.yml`


Dependencies
------------

ansible-scylla-node

Example Playbook
----------------

```yaml
---
- hosts: scylla-manager
  vars:
    scylla_clusters:
      - cluster_name: "mytestcluster"
        host: "{{ groups['scylla'][0]}}"
        auth_token_file: scyllamgr_auth_token.txt
        without_repair: false
    scylla_manager_repo_url: "http://downloads.scylladb.com/deb/ubuntu/scylladb-manager-2.1-bionic.list"
    #  These will be passed on to the ansible-scylla-node role applied to the Manager node in order to deploy a local Scylla instance
    scylla_manager_db_vars:
      scylla_repos:
        - 'http://repositories.scylladb.com/scylla/repo/../ubuntu/scylladb-4.1-bionic.list'
      # Only for Ubuntu/Debian
      scylla_repo_keyserver: 'hkp://keyserver.ubuntu.com:80'
      scylla_repo_keys:
        - 5e08fbd8b5d6ec9c
        - 6B2BFD3660EF3F5B
        - 17723034C56D4B19
      scylla_dependencies:
        - curl
        - wget

  roles:
    - role: ansible-scylla-manager

```


License
-------

BSD

Author Information
------------------

An optional section for the role authors to include contact information, or a website (HTML is not allowed).
