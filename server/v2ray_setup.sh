#!/usr/bash
sudo apt-get install wget -y

if [ "$?" -eq 0 ];then
    wget https://install.direct/go.sh | bash
    if [ "$?" -eq 0 ];then
        sudo service v2ray start
        if [ "$?" -eq 0 && -f /etc/v2ray/config.json ];then
            echo " v2ray installed."
        fi
    fi
fi
