#!/usr/bin/python3
import socket
import select

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

s.bind(('127.0.0.1',9999))
s.listen()

proxy = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
proxy.connect(('120.53.22.183',3306))

while True:
    rs,ws,es = select.select([s,proxy],[],[],20)
    clientt = None
    for r in rs:
        if r is s:
            clientt,addr= r.accept()
            data = clientt.recv(1024)
            print(data.decode('utf8'))

            proxy.send(data)
        elif r is proxy:
            data = r.recv(1024)
            if clientt:
                clientt.send(data)