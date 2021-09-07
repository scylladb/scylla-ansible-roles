#!/bin/bash

DIRS="`grep data_file_directories /etc/scylla/scylla.yaml`"
RC=$?

if [ $RC == 0 ]
then
DIR=$(grep -A1 data_file_directories /etc/scylla/scylla.yaml|grep -v 'data_file_directories:'|awk '{ print $NF }')
else
DIR="/var/lib/scylla/data"
fi

cd $DIR

echo "running on $HOSTNAME"

echo "cleaning first detected data dir:"
pwd

PATHS=$(du -m --max-depth=2 .|sort -k1h|awk -F"/" 'NF==3'|awk '{ print $NF}'|egrep -v '^./system/'\|'^./system_auth/'\|'^./system_distributed/'\|'^./system_traces/'\|'^./system_schema/')

for i in $PATHS; do
    TB=$(echo $i|awk -F'/' '{ print $NF }'|awk -F'-' '{ print $1 }')
    KS=$(echo $i|awk -F'/' '{ print $(NF - 1) }')
    echo "cleanup of $KS $TB"
    nodetool cleanup $KS $TB
done
