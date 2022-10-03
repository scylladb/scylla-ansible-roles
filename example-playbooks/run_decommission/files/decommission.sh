#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

echo "running on $HOSTNAME"
nodetool decommission

