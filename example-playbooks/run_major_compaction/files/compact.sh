#!/bin/bash

usage() {
    echo "Usage: $0 [-t KEYSPACE.TABLE] | [-k KEYSPACE] | -a " 1>&2
    echo "  -t : Specify a table, using the format KEYSPACE.TABLE" 1>&2
    echo "  -k : Specify a keyspace and compact all the tables within it" 1>&2
    echo "  -a : Compact all the keyspaces and tables on the node" 1>&2
    exit 0
}

get_schema() {
    DIR=$(grep -A1 data_file_directories /etc/scylla/scylla.yaml|grep -v 'data_file_directories:'|awk '{ print $NF }')
    cd $DIR
    PATHS=$(du -m --max-depth=2 .|sort -k1h|awk -F"/" 'NF==3'|awk '{ print $NF}'|egrep -v '^./system/'\|'^./system_auth/'\|'^./system_distributed/'\|'^./system_traces/'\|'^./system_schema/')
    echo "${PATHS}"
}

while getopts ":t:k:a" opt; do
    case "${opt}" in
        t)
            t=${OPTARG}
            ks=`echo $OPTARG|awk -F'.' '{ print $1 }'`
            tb=`echo $OPTARG|awk -F'.' '{ print $2 }'`
            PATHS=$(get_schema)
            res=0
            for i in `echo "$PATHS"`; do
                kspace=`echo $i|awk -F'/' '{ print $2 }'`
                table=`echo $i|awk -F'/' '{ print $3 }'|awk -F'-' '{ print $1 }'`
                if [ "$ks" == "$kspace" ] && [ "$tb" == "$table" ]; then
                    echo "Compacting $ks.$tb"
                    nodetool compact $ks $tb
                    res=1
                fi
            done
            if [ $res -ne 1 ]; then
                echo "$ks.$tb not found in the schema, exiting"
                exit 1
            fi
            ;;
        k)
            k=${OPTARG}
            PATHS=$(get_schema)
            res=0
            for i in `echo "$PATHS"`; do
                kspace=`echo $i|awk -F'/' '{ print $2 }'`
                table=`echo $i|awk -F'/' '{ print $3 }'|awk -F'-' '{ print $1 }'`
                if [ "$k" == "$kspace" ]; then
                    echo "Compacting $k.$table"
                    nodetool compact $k $table
                    res=1
                fi
            done
            if [ $res -ne 1 ]; then
                echo "$k not found in the schema, exiting"
                exit 1
            fi
            ;;
        a)
            PATHS=$(get_schema)
            res=0
            for i in `echo "$PATHS"`; do
                kspace=`echo $i|awk -F'/' '{ print $2 }'`
                table=`echo $i|awk -F'/' '{ print $3 }'|awk -F'-' '{ print $1 }'`
                echo "Compacting $kspace.$table"
                nodetool compact $kspace $table
            done
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))
