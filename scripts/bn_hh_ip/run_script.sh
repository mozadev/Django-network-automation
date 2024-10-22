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
    
done

echo -e "\n\n##############################\n\n"

for i in $cids;
do
    echo "$i $(grep -E '10\.' media/$i.log)"
done