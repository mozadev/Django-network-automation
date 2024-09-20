#!/bin/bash

cids=$(cat media/cid.txt)

for i in $cids;
do
    python main.py $i
    if [ $? -ne 0 ]; then
        echo "$i ERROR"
    else
        echo "$i EXITOSO"
    fi

    sleep 5
done