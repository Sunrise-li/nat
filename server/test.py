#!/usr/bin/python3

# coding:utf8
import socket
import select
import traceback
import  threading

server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
#server.setsockopt(socket.SOL_SOCKET,socket.SOCK_STREAM)

server.connect(('120.53.22.183',22))


proxy = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
proxy.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,2)
proxy.bind(('127.0.0.1',9999))
proxy.listen()

readable_list = []

readable_list.append(server)
readable_list.append(proxy)

max_len = 0xffffff

class TCPForword(threading.Thread):
    def __init__(self,server,client):
        threading.Thread.__init__(self)
        self.server = server
        print(server)
        print(client)
        self.client = client
        self.max_len = 1024
        self.activity = True
    
    def __stop(self):
        self.client.shutdown(2)
        self.server.shutdown(2)
        self.activity = False
    
    def run(self):
        while self.activity:
            try:
                rs,ws,es = select.select([self.server,self.client],[],[])
                for r in rs:
                    if r is self.server:
                        data = r.recv(self.max_len)
                        print('--------------------------------------------------------------')
                        print('server send: {0}'.format(data.decode('utf8')))
                        print('--------------------------------------------------------------')
                    
                        self.client.send(data)
                        if not data:
                            self.__stop()
                            break
                    elif r is self.client:
                        data = r.recv(self.max_len)
                        #print(r)
                        print('--------------------------------------------------------------')
                        print('client send: {0}'.format(data.decode('utf8')))
                        print('--------------------------------------------------------------')
                    
                        self.server.send(data)
            except Exception as e:
                break
        print('{0} 连接关闭'.format(self.client.getsockname()))
while True:

    try:
        rs,ws,es = select.select(readable_list,[],[],20)
        for r in rs:
            if r is proxy:
                client,addr  = proxy.accept()
                print('处理{0} 请求'.format(addr))
                t = TCPForword(server,client)
                t.start()
            elif r is server:
                data = server.recv(1024)
                if not data:
                    if not server:
                        server.connect(('120.53.22.183',3306))
                print('server : {0}'.format(data.decode('utf8')))


    except Exception as e:
        traceback.print_exc()
        print(e)









