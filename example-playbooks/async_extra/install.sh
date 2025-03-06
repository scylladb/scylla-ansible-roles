#!/usr/bin/env bash
# https://docs.ansible.com/ansible/latest/dev_guide/developing_locally.html

SCRIPT_DIR=$(dirname "$0")

mkdir -p ~/.ansible/plugins/action
mkdir -p ~/.ansible/plugins/modules
rm ~/.ansible/plugins/action/__pycache__/*

cp "$SCRIPT_DIR"/library/* ~/.ansible/plugins/modules/
cp "$SCRIPT_DIR"/action_plugins/* ~/.ansible/plugins/action/
