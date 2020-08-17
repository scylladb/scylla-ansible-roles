#!/usr/bin/env python

import requests
import yaml

class MyDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(MyDumper, self).increase_indent(flow, False)

r = requests.get('http://localhost:10000/failure_detector/endpoints/').json()

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
    t.append({'targets': d[dc], 'labels': {'cluster': 'mycluster1', 'dc': dc}})

#print(yaml.dump(t, encoding='utf8', allow_unicode=True, default_flow_style=False, explicit_start=True))
print(yaml.safe_dump(t, default_flow_style=False, indent=22))
