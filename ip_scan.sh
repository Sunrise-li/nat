#!/bin/bash

echo 'ip scan...'

echo 'start scan...'

echo 'get location address '

myip=`ifconfig en0 | awk '{print $2}' | egrep "^[1-2]\d{0,2}\.\d{1,3}"`
echo $myip
net_ip=${myip%.*}.

echo "start scan address :"$net_ip'1'

for scan_ip in $(seq 1 255);do
    nohup ping -c 3 $net_ip"$scan_ip" > /dev/null  && echo $net_ip"$scan_ip" >> ./up_host 2>&1 &
done
cat ./up_host
exit