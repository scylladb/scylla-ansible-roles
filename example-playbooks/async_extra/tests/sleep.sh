#!/bin/sh

echo '{"job": false}'

if [ -z "$1" ]; then
  echo "error: argument missing" > /dev/stderr
  exit 1
fi

sleep "$1"

echo '{"job": true}'
