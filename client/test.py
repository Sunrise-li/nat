#!/usr/bin/python3


import socket
import select


s1 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s1.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
s1.connect(('120.53.22.183',8011))


s2 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s2.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
s2.connect(('120.53.22.183',8011))


read_list = [s1,s2]

while True:
    rs,ws,es = select.select(read_list,[],[])
    for sock in rs:
        
        data = sock.recv(1024)

        print('recelve {0}'.format(data))
