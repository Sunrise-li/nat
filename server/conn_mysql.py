#!/usr/bin/python3
import socket

# server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
# server.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
# server.connect(('120.53.22.183',3306))
# print(server.recv(0xffff).decode('gbk'))


proxy = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

proxy.bind(('127.0.0.1',8888))
proxy.listen()

while True:
    client,adde= proxy.accept()
    print(client.recv(0xffff).decode('utf8'))
