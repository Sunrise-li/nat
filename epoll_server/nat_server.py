#!/usr/bin/python3

import select
import socket
import queue
from concurrent.futures import ThreadPoolExecutor


class NATServer:
    def tcp_forword(self,nat_server,new_sock):
        print('tcp_forword....')
        server = nat_server
        client = new_sock
        server.setblocking(False)
        client.setblocking(False)
        read_list = [server,client]
        activity = True
        while activity:
            rs,ws,es = select,select(read_list,[],[])
            for r in rs:
                if r is client:
                    data = r.recv(self.max_len)
                    server.sendAll(data)
                    if not data:
                        activity = False
                elif r is server:
                    data = r.recv(self.max_len)
                    client.sendAll(data)
                    if not data:
                        activity = False
        self.nat_serv_socks.put(server)
        return True

    def __init__(self):
        self.init_thread_pool()
        self.init_server_sock()
        self.nat_serv_socks = queue.Queue(10)
        self.init_nat_serv_sock()
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
    
    def init_nat_serv_sock(self):
        self.nat_serv_sock_port = 3306

        print('nat sock 注册端口 {0}'.format(self.nat_serv_sock_port))
        nat_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        nat_sock.connect(('120.53.22.183',self.nat_serv_sock_port))
        #nat_sock.listen()
        # while self.nat_serv_socks.qsize() < 10:
        #     new_sock,addr = nat_sock.accept()
        self.nat_serv_socks.put(nat_sock)


    def start(self):
        read_list = [self.server_socket]
        
        while True:
            rs,ws,es = select.select(read_list,[],[])
            for r in rs:
                try:
                    print('fid {0}  fid{1}'.format(r.fileno(),self.server_socket.fileno()))
                    print(r.fileno() == self.server_socket.fileno())
                    if r.fileno() == self.server_socket.fileno():
                        new_client,new_addr = self.server_socket.accept()
                        print('{0} connect success.'.format(new_addr))
                        new_sock_fd = new_client.fileno()
                        # self.sock_conns[new_sock_fd] = new_client;
                        # self.sock_addrs[new_sock_fd] = new_addr()
                        read_list.append(new_client)
                    else:
                        nat_sock = self.nat_serv_socks.get()
                        print('开始转发数据包。。。{0} ----{1}'.format(nat_sock,r))
                        future = self.forword_pool.submit(self,self.tcp_forword,(nat_sock,r))
                        read_list.remove(r)
                        print(future.result())
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






