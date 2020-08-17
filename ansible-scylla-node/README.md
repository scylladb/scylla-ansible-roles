ansible-scylla-node
=========

Deploy a Scylla cluster 


Requirements
------------

- Ansible 2.8 or higher
- Python 3.x

Role Variables
--------------

Please check under `defaults/main.yml` and `vars/main.yml`, the variables are heavily commented

Dependencies
------------
    Recommended in order to enable extra swap and configure a RAID array
    - geerlingguy.swap
    - mrlesmithjr.mdadm


Example Playbook
----------------

```yaml
---
- name: Scylla node
  hosts: scylla
  become: true
  vars:
    #variables for the mdadm role
    mdadm_arrays:
    - name: 'md0'
      devices:
        - '/dev/nvme0n1'
        - '/dev/nvme1n1'
        - '/dev/nvme2n1'
      filesystem: 'xfs'
      level: '0'
      mountpoint: '/var/lib/scylla'
      state: 'present'
      opts: 'noatime,nofail'

    #variables for the swap role
    swap_file_size_mb: '1024'

    # variables for the Scylla node role (can be set here or in the role's vars/main.yml)
    scylla_repos:
      - 'http://repositories.scylladb.com/scylla/repo/613b5a39-91d7-4267-aa15-4384fde87442/ubuntu/scylladb-4.1-bionic.list'
    scylla_repo_keyserver: 'hkp://keyserver.ubuntu.com:80'
    scylla_repo_keys:
      - 5e08fbd8b5d6ec9c
      - 6B2BFD3660EF3F5B
      - 17723034C56D4B19
    scylla_dependencies:
      - curl
      - wget
    scylla_version: latest
    scylla_edition: oss
    scylla_cluster_name: 'testcluster'
    scylla_snitch: GossipingPropertyFileSnitch
    scylla_io_probe: True
    enable_mc_format: true
    scylla_seeds:
      - "{{ groups['scylla'][0] }}"
      - "{{ groups['scylla'][1] }}"
    scylla_api_address: '127.0.0.1'
    scylla_api_port: '10000'
    generate_monitoring_config: True
    scylla_manager_enabled: true
    scylla_manager_repo_url: "http://downloads.scylladb.com/deb/ubuntu/scylladb-manager-2.1-bionic.list"

  tasks:
    # Workaround for some Debian versions that might not have XFS support out of the box
    - name: install XFSprogs
      package:
        name: xfsprogs
        state: present
      become: true
  roles:
    - geerlingguy.swap
    - mrlesmithjr.mdadm
    - ../ansible-scylla-node
```


License
-------

Apache

