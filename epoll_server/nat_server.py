#!/usr/bin/python3

import select

import socket
import queue
import traceback

from concurrent.futures import ThreadPoolExecutor

max_len = 0xffffff

nat_serv_socks = queue.Queue(10)

nat_serv_sock_port = 80

nat_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
#nat_sock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
#mysql
#nat_sock.connect(('120.53.22.183',nat_serv_sock_port))

nat_sock.connect(('104.193.88.123',nat_serv_sock_port))

#nat_sock.listen()
# while self.nat_serv_socks.qsize() < 10:
#     new_sock,addr = nat_sock.accept()
nat_serv_socks.put(nat_sock)

def tcp_forword(nat_server,new_sock):
    print('tcp_forword....')
    server = nat_server
    client = new_sock
    server.setblocking(False)
    client.setblocking(False)
    read_list = [server,client]
    activity = True
    print(client)
    print(server)
    try:
        while activity:
            rs,ws,es = select.select(read_list,[],[],300)
            if not rs and not ws and not es:
                activity = False
                client.close()
            for r in rs:
                if r is client:
                    data = r.recv(max_len)
                    print('client recv {0}'.format(data))
                    server.sendall(data)
                    if not data:
                        activity = False
                elif r is server:
                    data = r.recv(max_len)
                    print('server recv {0}'.format(data))
                    client.sendall(data)
                    if not data:
                        activity = False
    except Exception as e:
        traceback.print_exc()
    print('连接关闭。。。')
    nat_serv_socks.put(server)
    return True

class NATServer:
    def __init__(self):
        self.init_thread_pool()
        self.init_server_sock()
      
        #self.init_nat_serv_sock()
        #self.forword_pool.submit(self.init_nat_serv_sock,())
        #self.init_epoll()

        self.sock_addrs = {}
        self.sock_conns = {}
        self.max_len = 0xffffff

    def init_thread_pool(self):
        self.core_pool_size = 10
        self.forword_pool = ThreadPoolExecutor(self.core_pool_size)
    def init_server_sock(self):
        self.server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server_socket.bind(('',8080))
        self.server_socket.listen(10)

    def init_epoll(self):
        self.epoll = select.epoll()
        self.epoll.register(self.server_socket.fileno(),select.EPOLLIN)
    


    def start(self):
        read_list = [self.server_socket]
        
        while True:
            rs,ws,es = select.select(read_list,[],[])
            for r in rs:
                try:
                    print('fid {0}  fid{1}'.format(r.fileno(),self.server_socket.fileno()))
                    if r.fileno() == self.server_socket.fileno():
                        new_client,new_addr = self.server_socket.accept()
                        print('{0} connect success.'.format(new_addr))
                        nat_sock = nat_serv_socks.get()
                        new_sock_fd = new_client.fileno()
                        print('client fd {0} server fd{1}'.format(new_sock_fd,nat_sock.fileno()))
                        # self.sock_conns[new_sock_fd] = new_client;
                        # self.sock_addrs[new_sock_fd] = new_addr()
                       
                        future = self.forword_pool.submit(tcp_forword,nat_sock,new_client)
                        # read_list.remove(r)
                        #read_list.append(new_client)
                    # else:
                        
                    #     print('开始转发数据包。。。{0} ----{1}'.format(nat_sock,r))
                    #     future = self.forword_pool.submit(tcp_forword,(nat_sock,r))
                    #     read_list.remove(r)
                    #     print(future.result())
                except Exception  as e:
                    print(e)
                   
                
            #epoll_list = self.epoll.poll()
            # for fd,events in epoll_list:
            #     if fd == self.server_socket.fileno():
            #         new_client,new_addr = self.server_socket.accept()
            #         new_sock_fd = new_client.fileno()
            #         #注册新sock
            #         self.sock_conns[new_sock_fd] = new_client;
            #         self.sock_addrs[new_sock_fd] = new_addr()
            #         self.epoll.register(new_sock_fd,select.EPOLLIN)
            #     elif events & select.EPOLLIN:
            #         nat_sock = self.nat_serv_socks.get()
            #         client = self.sock_conns[df]
            #         self.forword_pool.submit(self.tcp_forword,(nat_sock,client))
            #         self.epoll.unregister(fd)
            #         del self.sock_addrs[fd]
            #         del self.sock_conns[fd]

if __name__ == "__main__":
    server = NATServer()
    server.start()






