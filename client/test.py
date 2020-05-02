#!/usr/bin/python3


import socket
import select
import threading

mysql = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
mysql.connect(('172.20.10.4',3306))


server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
#server.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)

server.bind(('0.0.0.0',3336))
server.listen()

buff_size = 0xffff

def tcp_forword(nat_client,client,timeout=60):
    nat_client = nat_client
    client = client
    #sock 文件描述符
    nat_client_fd = nat_client.fileno()
    print('nat_client_fd {0}'.format(nat_client_fd))
    client_fd = client.fileno()
    print('client_fd {0}'.format(client_fd))
    activity = True
    #data = client.recv(buff_size)
    #print('client-first-data {0}'.format(data))
    #nat_client.send(data)
    read_list = [nat_client,client]
    
    while activity:
        print(read_list)
        try:
            rs,ws,es = select.select(read_list,[],[],10)
            # if not rs and not ws and not es:
            #     activity = False
            #     nat_client.send(EOF)
            #     nat_client.close()
            #     client.close()
            #     break
            for sock in rs:
                print(sock)
                data = sock.recv(buff_size)
                print('data {0}'.format(data))
                if b'HEART' in data:
                    if sock.fileno == client_fd:
                        keep_alive = 'KEEPALIVE'.encode('utf8')
                        sock.send(keep_alive)
                    continue
                if not data:
                    activity = False
                    client.close()
                    nat_client.close()
                    break
                if sock.fileno() == nat_client_fd:
                    client.send(data)
                elif sock.fileno() == client_fd:
                    #客户端返回空数据表示连接结束
                    nat_client.send(data)
        except Exception as e:
            nat_client.close()
            client.close()
            activity = False

while True:
    client,addr = server.accept()
    t = threading.Thread(target=tcp_forword,args=(mysql,client,))
    t.start()
