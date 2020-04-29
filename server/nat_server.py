#!/usr/bin/python3
import socket
import select
import threading
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

worker_pool = ThreadPoolExecutor(20)
#服务注册
register_servers = {}

#nat配置
nat_config = {}
#sock_connect_queue = queue.Queue(10)

evn="product"
# 远程内网注册端口
nat_port = 6783
#客户端请求端口
server_port = 8080
nat_sock_connects = {}

class Server:
    def __init__(self,config):
        self.name = config['server_name']
        self.src_port = config['src_port']
        self.dst_port = config['dst_port']
        self.timeout = config['timeout'] if config['timeout'] else 10
        self.init_server_sock()

    def init_server_sock(self):
        self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0',self.dst_port))
        self.server.listen()

""" 初始化内网连接 """
def nat_register():
    register_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    register_sock.bind(('',nat_port))
    register_sock.listen()
    while True:
        sock_connect,addr = register_sock.accept()
        print('{0}:{1} connect...'.format(addr[0],addr[1]))
        data = sock_connect.recv(1024)
        if str(addr[1]) in nat_sock_connects.keys():
            if b'HEART' in data:
                register_server.send('KEEPALIVE')
        else:
            server_info = data.decode('utf8')
            port = server_info.split(':')[1]
            nat_sock_connects[port] = sock_connect
""" 接收处理客户端请求 """
def start():
    #nat_server_mapper = {}
    server_socks = []
    # server_timeout = {}
    # server_names = {}
    servers_fd = {}
    for server in register_servers.values():
        server_socks.append(server.server)
        #sock 和客户端口映射
        servers_fd[server.server.fileno()] = server
    while True:
        try:
            rs,ws,es = select.select(server_socks,[],[])
            for server in rs:
                # 判断服务是否已经注册
                fd = server.fileno()
                if fd in servers_fd.keys():
                    client,addr = server.accept()
                     #转发请求
                    #查找对应端口好进行数据转发
                    ser_sock = servers_fd[fd]
                    #通过端口好找到转发的socket进行转发
                    src_port = str(ser_sock.src_port)
                    if str(src_port) in nat_sock_connects.keys():
                        nat_sock = nat_sock_connects[src_port]
                        #超时时间
                        timeout = ser_sock.timeout
                        #交给线程池处理
                        worker_pool.submit(ip_forword,nat_sock,client,timeout,ser_sock.name)
        except Exception as e:
            traceback.print_exc()

"""初始化服务器映射端口进程"""  
def register_server():
    for server_name in nat_config.keys():
        config = nat_config[server_name]
        if config['server_name'] and str(config['src_port']) and str(config['dst_port']):
            register_servers[server_name] = Server(config)
        else:
            print('erro server {0}'.format(config['server_name']))
    
#两个sock 之间转发数据包
def ip_forword(sock_server,sock_client,timeout,server_name,read_len=0xFFFF):

    print('--------开始数据转发---------')
    sock_server = sock_server
    sock_client = sock_client
    read_list = [sock_client,sock_server]
    #sock 文件描述符
    server_fd = sock_server.fileno()
    client_fd = sock_client.fileno()
    activity = True
    while activity:
        try:
            rs,ws,es = select.select(read_list,[],[],timeout)
            if not rs and not ws and not es:
                activity = False
            for sock in rs:
                data = sock.recv(read_len)
                if b'HEART' in data:
                    if sock.fileno == client_fd:
                        keep_alive = 'KEEPALIVE'.encode('utf8')
                        sock.send(keep_alive)
                    continue
                if sock.fileno() == server_fd:
                    sock_client.send(data)
                elif sock.fileno() == client_fd:
                    sock_server.send(data)
        except Exception as e:
            traceback.print_exc()

def load_config():
    config_file = open('config.json','r')
    config = config_file.read()
    config_file.close()
    config_objs = json.loads(config)
    for conf in config_objs:
        nat_config[conf['server_name']] = conf


def main():
    #加载配置文件
    load_config()
    #注册服务
    register_server()
    #注册内网穿透端口
    register = threading.Thread(target=nat_register)
    #启动服务
    server= threading.Thread(target=start)
    register.start()
    time.sleep(5)
    server.start()
    register.join()
    server.join()
if __name__ == "__main__":
    main()






