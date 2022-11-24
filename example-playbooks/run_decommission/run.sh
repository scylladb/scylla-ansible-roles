#!/bin/bash

set -o errexit
set -o pipefail
# set -o nounset
# set -o xtrace

# Set magic variables for current file & dir
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTRA="$DIR/async_extra"

if [ -z "$1" ]; then
  echo "error: limit is required"
  exit 1
fi

ANSIBLE_ACTION_PLUGINS=$EXTRA/action_plugins ansible-playbook ./run_decommission.yml -vvvv -M $EXTRA/library -l $1
