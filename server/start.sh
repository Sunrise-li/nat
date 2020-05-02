#!/bin/bash

ps -ef | grep nat_server | grep -v grep | awk '{print $2}' | xargs -n1 -I {} kill -9 {}

if [ "$?" -eq 0 ];then
    sudo nohup ./select_nat_server.py 8011 > server.log 2>&1 &
fi