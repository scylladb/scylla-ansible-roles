#!/bin/sh
# https://docs.ansible.com/ansible/latest/dev_guide/developing_locally.html

mkdir -p ~/.ansible/plugins/action
mkdir -p ~/.ansible/plugins/modules
rm ~/.ansible/plugins/action/__pycache__/*

cp ./library/* ~/.ansible/plugins/modules/
cp ./action_plugins/* ~/.ansible/plugins/action/
