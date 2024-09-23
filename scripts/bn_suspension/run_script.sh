#!/bin/bash

while IFS=, read -r line; do
    #echo "$line"
    python main.py $line
done < media/pe_interface.txt