#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

DIR="/var/lib/scylla/data"
CONF="/etc/scylla/scylla.yaml"

if [ -f "$CONF" ]; then
    if grep -q data_file_directories "$CONF"; then
        DIR=$(grep -A1 data_file_directories "$CONF" | grep -v 'data_file_directories:' | awk '{ print $NF }')
    fi
fi

if [ ! -d "$DIR" ]; then
    echo "error: $DIR does not exist"
    exit 1
fi

echo "running on $HOSTNAME"

cd "$DIR"
echo "cleaning first detected data dir:"; pwd

PATHS=$(du -m --max-depth=2 .|sort -k1h|awk -F"/" 'NF==3'|awk '{ print $NF}'|grep -E -v '^./system/'\|'^./system_auth/'\|'^./system_distributed/'\|'^./system_traces/'\|'^./system_schema/')

for i in $PATHS; do
    TB=$(echo "$i"|awk -F'/' '{ print $NF }'|awk -F'-' '{ print $1 }')
    KS=$(echo "$i"|awk -F'/' '{ print $(NF - 1) }')
    echo "evaluating $DIR/$i/"
    if compgen -G "$DIR/$i/*.db" > /dev/null; then
        echo "cleanup of $KS $TB"
        nodetool cleanup "$KS" "$TB"
    else
        echo "skipping $KS $TB since it has no sstables and likely is dropped"
    fi
done
