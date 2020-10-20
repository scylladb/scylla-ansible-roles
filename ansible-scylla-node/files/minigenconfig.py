import subprocess
import yaml
import sys
import argparse
import json
from time import sleep

def read_endpoints(r):
    succ = False
    t = []
    d = {}
    try:
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
        ret = yaml.safe_dump(t, default_flow_style=False, indent=2)
        succ = True
    except:
        succ = False
        ret = ''
    return succ, ret

parser = argparse.ArgumentParser(description='Generates a scylla_servers.yml standard file form the data stored on a cluster node. Run on any node in cluster')
parser.add_argument('--cluster-name', help='Scylla cluster name', default='mycluster', required=False)
parser.add_argument('--api-string', help='Scylla API URL, ex: http://localhost:10000', default='http://localhost:10000', required=False)
args = parser.parse_args()

#r = requests.get(args.api_string + '/failure_detector/endpoints/').json()
url = args.api_string + '/failure_detector/endpoints/'
retries = 5
success = False

while not success and retries > 0:
    sleep(3)
    r = json.loads(subprocess.check_output(['curl', '-s', url]))
    success, out = read_endpoints(r)

if success:
    print(out)
else:
    print("Failed to read and parse %s" % str(r))
    sys.exit(1)