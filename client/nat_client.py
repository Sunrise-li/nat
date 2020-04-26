#!/usr/bin/python3
import socket
import select
import threading
import json
import time
from concurrent.futures import ThreadPoolExecutor

import multiprocessing as process


worker_pool = ThreadPoolExecutor(20)
#配置文件
nat_config = {}

#本地服务
local_servers = {}
#内网穿透sock 负责和服务器建立长连接转发数据包
nat_socks = {}

def heart():
    while(True):
        for server_name in local_servers.keys():
            try:
                local_servers[server_name].sendall(b'HEART')
            except Exception as e:
                config = nat_config[server_name]
                create_local_server_keepalive_connect(config)

        for server_name in nat_socks.keys():
            try:
                nat_socks[server_name].sendall(b'HEART')
            except Exception as e:
                config = nat_config[server_name]
                create_net_keepalive_connect(config)
        time.sleep(5)
#和公网服务器创建长连接
def create_net_keepalive_connect(config):
    server_name = config['server_name']
    if server_name in nat_socks.keys():
        del nat_socks[server_name]
    nat_port = config['nat_port']
    net_addr = config['net_addr']
    net_port = config['net_port']
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
    print('nat port {0}'.format(nat_port))
    # sock.bind(('0.0.0.0',nat_port))
  
    sock.connect((net_addr,net_port))
    data = ('{0}:{1}'.format(server_name,nat_port)).encode('utf8')

    sock.sendall(data)
    nat_socks[server_name] = sock

#和本地服务创建长连接 
def create_local_server_keepalive_connect(config):
    server_name = config['server_name']
    if server_name in local_servers.keys():
        del local_servers[server_name]
    local_port = config['local_port']
    local_addr = config['local_addr']
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
    server.connect((local_addr,local_port))
    local_servers[server_name] = server

def nat_handler(server_name,server,nat_sock):
    server_name = server_name
    server = server
    nat_sock = nat_sock
    s_fd = server.fileno()
    n_fd  = nat_sock.fileno()
    read_list = [server,nat_sock]
    while True:
        rs,ws,es = select.select(read_list,[],[])
        for sock in rs:
            fd = sock.fileno()
            try:
                data = sock.recv(0xffff)
                print('data : {0}'.format(data))
                if not data:
                    sock.close()
                if b'KEEPALIVE' in data:
                    continue;
                if fd == s_fd:
                    nat_sock.sendall(data)
                elif fd == n_fd:
                    server.sendall(data)
            except Exception as e:
                if fd == s_fd:
                    config = nat_config[server_name]
                    create_local_server_keepalive_connect(config)
                elif fd == n_fd:
                    config = nat_config[server_name]
                    create_net_keepalive_connect(config)

def start():
    load_config()
    init_nat()
    process_list = []
    for server_name in nat_config.keys():
        server = local_servers[server_name]
        nat = nat_socks[server_name]
        p = process.Process(target=nat_handler,args=(server_name,server,nat))
        process_list.append(p)

    for p in process_list:
        p.start()

    #开启心跳
    heart()

def main(start):
    start()


# def start():
#     sock_fd_mapping  = {}
#     socks  = {}
#     read_list = []
#     for server_name in nat_socks.keys():
#         nat = nat_socks[server_name]
#         server = local_servers[server_name]
#         read_list.append(nat)
#         read_list.append(server)
#         nat_fd = nat.fileno()
#         server_fd = server.fileno()
#         sock_fd_mapping[nat_fd] = server_fd
#         sock_fd_mapping[server_fd] = nat_fd
#         socks[nat_fd] = nat
#         socks[server_fd] = server
#     while True:
#         rs,ws,es = select.select(read_list,[],[])
#         for sock in rs:
#             fd = sock.fileno()
#             data = sock.recv(0xffff)
#             if not data:
#                 sock.close()
#             if b'KEEPALIVE' in data:
#                 continue;
#             if fd in sock_fd_mapping.keys():
#                 dst_fd = sock_fd_mapping[fd]
#                 if dst_fd and dst_fd in socks.keys():
#                     socks[dst_fd].sendall(data)


def init_nat():
    for config in nat_config.values():
        """
            server_name:服务名称 不能重复
            local_port :本地服务端口
            local_addr :本地服务ip
            nat_port   :本地内网穿透监听端口
            net_addr   :内网穿透服务器地址
            net_port   :内网穿透服务注册端口
        
        """
        print(config)
        create_local_server_keepalive_connect(config)
        create_net_keepalive_connect(config)

def load_config():
    config_file = open('config.json','r')
    config = config_file.read()
    config_file.close()
    config_objs = json.loads(config)
    for conf in config_objs:
        nat_config[conf['server_name']] = conf


if __name__ == "__main__":
    start()