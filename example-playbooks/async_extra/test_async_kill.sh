#!/bin/sh

echo "{ \"ANSIBLE_MODULE_ARGS\": { \"alias\": \"$1\", \"_async_dir\": \"$HOME/.ansible_async\" } }" | PYTHONPATH=library python -m async_kill
