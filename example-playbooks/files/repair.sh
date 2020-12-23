#!/bin/bash

DIR=$(grep -A1 data_file_directories /etc/scylla/scylla.yaml|grep -v 'data_file_directories:'|awk '{ print $NF }')

cd $DIR
pwd

PATHS=$(du -m --max-depth=2 . | sort -k1h | awk -F"/" 'NF==3'|awk '{print $NF}')

for i in $PATHS; do
    TB=$(echo $i|awk -F'/' '{ print $NF }'|awk -F'-' '{ print $1 }')
    KS=$(echo $i|awk -F'/' '{ print $(NF - 1) }')
    nodetool cleanup $KV $TB
done
