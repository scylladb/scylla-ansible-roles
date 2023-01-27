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
    - mrlesmithjr.mdadm
    - ../ansible-scylla-node
```

### `scylla_version` format
`scylla-version` can be either a string 'latest' or an explicit version that needs to be installed.
If 'latest' is requested a corresponding (OSS or Enterprise) most recent official version is going to be
installed.

An explicit version string can be either a full version string, like `2021.1.1-0.20210530.ddf65ffc2-1`
or any prefix of it that ends with a non-digit character, e.g. `2021.1.1`, `2021.1.1-0.20210530.ddf65ffc2`,
`2021.1.1-0.20210530`, etc.

If a give string matches zero or more than an exactly one existing version it is going to trigger
a play failure with a corresponding error message:

```commandline
TASK [Error out, wrong Scylla version was passed (more than a single or none version matches), please fix it!] *************************************************************************************************************************
fatal: [localhost]: FAILED! => {"changed": false, "msg": "Too many/few choices for a requested version '2021.1': ['2021.1.0-0.20210511.9e8e7d58b-1', '2021.1.1-0.20210530.ddf65ffc2-1', '2021.1.10-0.20220410.e8e681dee-1', '2021.1.11-0.20220516.8e6c9917c-1', '2021.1.12-0.20220620.e23889f17-1', '2021.1.2-0.20210620.7bb9428ae-1', '2021.1.3-0.20210708.aec1c25d7-1', '2021.1.4-0.20210721.6cb3fc153-1', '2021.1.5-0.20210818.fc817c0cd-1', '2021.1.6-0.20211006.5eee352bf-1', '2021.1.7-0.20211108.3c0706646-1', '2021.1.8-0.20220106.fcdf103fd-1', '2021.1.9-0.20220208.86e3ea4df-1', '2021.1~rc2-0.20210502.f3e5e1f12-1']. Bailing out!"}
```

License
-------

Apache

