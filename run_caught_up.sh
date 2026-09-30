#!/bin/bash
result=$(find . -maxdepth 1 -type d -name '.venv*' -print -quit)
[ -n "$result" ]
is_venv=$?
activate_path="$result/bin/activate"
# we need to check if a virtual env should be used
if [ $is_venv -eq 0 ]; then
    source $activate_path
else
    echo "No virtual env is used global libraries"
fi
cd ./src/core/
python cli.py
cd ../../
# exit the venv is also important
if [ $is_venv -eq 0 ]; then
    deactivate
fi
