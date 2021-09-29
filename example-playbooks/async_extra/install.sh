#!/bin/sh
# https://docs.ansible.com/ansible/latest/dev_guide/developing_locally.html

mkdir -p ~/.ansible/plugins/action
mkdir -p ~/.ansible/plugins/modules

cp ./library/* ~/.ansible/plugins/modules/
cp ./action_plugins/* ~/.ansible/plugins/action/
