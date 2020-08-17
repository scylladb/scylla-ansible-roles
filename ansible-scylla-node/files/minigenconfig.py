#!/usr/bin/env python
import subprocess
import yaml
import sys
import argparse
import json

parser = argparse.ArgumentParser(description='Generates a scylla_servers.yml standard file form the data stored on a cluster node. Run on any node in cluster')
parser.add_argument('--cluster-name', help='Scylla cluster name', default='mycluster', required=False)
parser.add_argument('--api-string', help='Scylla API URL, ex: http://localhost:10000', default='http://localhost:10000', required=False)
args = parser.parse_args()

#r = requests.get(args.api_string + '/failure_detector/endpoints/').json()
url = args.api_string + '/failure_detector/endpoints/'
r = json.loads(subprocess.check_output(['curl', '-s', url]))
t = []
d = {}
for node in r:
    addrs = node['addrs']
    for appstate in node['application_state']:
        if appstate['application_state'] == 3:
            dc = appstate['value']
    if dc not in d.keys():
        d[dc] = [addrs]
    else:
        d[dc].append(addrs)
for dc in d.keys():
    t.append({'targets': d[dc], 'labels': {'cluster': args.cluster_name, 'dc': dc}})
print(yaml.safe_dump(t, default_flow_style=False, indent=2))
