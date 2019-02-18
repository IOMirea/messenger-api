#!/bin/bash

while true; do
    # git reset --hard
    git pull origin master

    python3 src/app.py
    exit_code=$?

    if [ $exit_code == 2 ]
    then
        echo "Terminate exit code recieved. Exiting"
        break
    elif [ $exit_code == 3 ]
    then
        seconds=1
        echo "Restarting without delay"
    else
        seconds=15
    fi

    for ((second=$seconds; second > 0; second--))
    do
        echo -ne "Restarting in $second seconds..\r"
        sleep 1
    done

    echo
done
