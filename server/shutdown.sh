#/bin/bash
ps -ef | grep nat_server | grep -v grep | awk '{print $2}' | xargs -n1 -I {} kill -9 {}
