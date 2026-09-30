#!/bin/bash
if alias caughtup >/dev/null 2>&1; then
    echo "alias found"
else
    echo "alias caughtup not found"
    cur_dir=$(pwd)
    exec_path="$cur_dir/run_caught_up.sh"
    alias caughtup="$exec_path"
    echo "alias created for caughtup app"
fi
