#!/bin/bash

while true; do
    # git reset --hard
    git pull origin master

    python3 migrations/migrate.py
    exit_code=$?

    if [ $exit_code != 0 ]
    then
        # at this point database is broken
        echo "[SH]Migration script exited with error code $exit_code. Exiting"
        break
    fi

    python3 iomirea/app.py "$@"
    exit_code=$?

    if [ $exit_code == 2 ]
    then
        echo "[SH]Terminate exit code recieved. Exiting"
        break
    elif [ $exit_code == 3 ]
    then
        seconds=1
        echo "[SH]Restarting without delay"
    else
        seconds=15
    fi

    for ((second=$seconds; second > 0; second--))
    do
        echo -ne "[SH]Restarting in $second seconds..\r"
        sleep 1
    done

    echo
done
