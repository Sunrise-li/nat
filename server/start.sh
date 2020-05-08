#!/bin/bash

ps -ef | grep nat_server | grep -v grep | awk '{print $2}' | xargs -n1 -I {} kill -9 {}

if [ "$?" -eq 0 ];then
    nohup python3 nat_server.py -l 8011 -k ~/.ssh/pub_key > server.log 2>&1 &
    if [ "$?" -eq 0 ];then
        echo "服务启动成功."
    else
        echo "服务启动失败"
    fi
fi
