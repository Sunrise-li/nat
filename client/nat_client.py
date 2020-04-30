#!/usr/bin/python3
import socket
import select
import threading
import json
import time
import rsa 
import os
import hashlib
import traceback
import multiprocessing as process
from concurrent.futures import ThreadPoolExecutor 
from concurrent.futures import ThreadPoolExecutor



worker_pool = ThreadPoolExecutor(20)
#配置文件
nat_config = {}
#nat服务 文件描述符  和本地服务地址映射 用于多服务注册转发
nat_client_fd_local_server = {}


#内网穿透sock 负责和服务器建立长连接转发数据包
nat_clients = {}

buff_size = 0xffff

EOF = b'\r\n\r\n0000\r\n\r\n'

#活动中的进程
alive_processs = {}
#rsa 配置私钥
priv_key_path = os.path.join(os.getenv('HOME'),'.ssh/priv_key')
f = open(priv_key_path)
priv_key = rsa.PrivateKey.load_pkcs1(f.read())
f.close()

#心跳包
def heart():
    pass

#和公网服务器创建长连接
def register_nat_keepalive_connect(config):
    #nat映射公网端口
    nat_server_port         = config['nat_server_port']
     #nat服务注册IP
    net_server_ip           = config['net_server_ip']
    #nat服务铸错端口
    register_server_port    = config['register_server_port']
    #本地服务监听端口
    nat_server_port         = config['nat_server_port']
    #需要穿透的本地服务名称
    local_server_name       = config['local_server_name']
    #本地服务地址
    local_server_ip         = config['local_server_ip']
    #本地服务监听端口
    local_server_port       = config['local_server_port']
    #超时时间 
    timeout                 = config['timeout']
    server_addr = '{0}:{1}'.format(net_server_ip,nat_server_port)
    if server_addr in nat_clients.keys():
        nat_clients[server_addr].close()
        del nat_clients[server_addr]
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
    print('connect {0}:{1}'.format(net_server_ip,register_server_port))
    sock.connect((net_server_ip,register_server_port))
    #ssh:8022
    #计算本地唯一摘要

    signature = hashlib.sha256(json.dumps(config).encode('utf8')).hexdigest()
    data = {
        'server_name':local_server_name,
        'timeout':timeout,
        'nat_port':nat_server_port,
        'signature':signature
    }
    #向服务端发送注册信息
    data_bytes= json.dumps(data).encode('utf8')
    #发送注册信息
    print('开始注册服务{0} 端口{1}'.format(local_server_name,nat_server_port))
    sock.send(data_bytes)
    id_auth = sock.recv(1024)
    #身份验证
    auth = rsa_decrypt(id_auth);
    print('身份认证:{0}'.format(auth))
    sock.send(auth)
    auth_res = sock.recv(1024)
    if b'ok' in auth_res:
        print('身份认证成功')
        #注册服务
        nat_clients[server_addr] = sock
        print(sock)
        sock_fd = sock.fileno()
        if sock_fd in nat_client_fd_local_server.keys():
            del nat_client_fd_local_server[sock_fd]
            nat_client_fd_local_server[sock_fd] = '{0}:{1}'.format(local_server_ip,local_server_port)
        return sock
    return None

def rsa_decrypt(ciphertext):
    return rsa.decrypt(ciphertext,priv_key)
    

#创建本地服务连接
#本地服务IP local_server_ip
#本地服务监听端口  local_server_port
def create_local_server_connect(local_server_ip,local_server_port,keep_alive=False):
    local_server_addr = '{0}:{1}'.format(local_server_ip,local_server_port)
    local_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    if keep_alive:
        #长连接
        local_server.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
    local_server.connect((local_server_ip,local_server_port))
    return local_server

#处理用户情求 默认超时时间1分钟
def server_handler(nat_client,timeout=69):
    
    nat_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    nat_client_fd = nat_client.fileno()
    if nat_client_fd not in nat_client_fd_local_server.keys():
        return 
    #通过nat 客户端文教描述符取出对应本地服务地址
    local_server_addr = nat_client_fd_local_server[nat_client_fd];
    #解析地址
    local_server_ip_port = local_server_addr.split(':')
    local_server_ip = local_server_ip_port[0]
    local_server_port = local_server_ip_port[1]
    #获取本地连接
    local_server = create_local_server_connect(local_server_ip,local_server_port)
    local_server_fd = local_server.fileno()
    read_list = [nat_client,local_server]
     #读取数据
    data_bytes = nat_client.recv(buff_size)
    local_server.send(data_bytes)
    activity = True
    while activity:
        try:
            rs,ws,es = select.select(read_list,[],[],timeout)
            for sock in rs:
                data_bytes = sock.recv(buff_size)
                #将数据转发对方
                if sock.fileno() == nat_client_fd:
                    #收到结束符关闭连接
                    if EOF in data_bytes:
                        local_server.close()
                        nat_client.close()
                        activity = False
                    local_server.send(data_bytes)
                elif sock.fileno() == local_server_fd():
                     #没有数据 结束当前会话
                    if not data_bytes:
                          #发送结束符
                        nat_client.send(EOF)
                        local_server.close()
                        nat_client.close()
                        activity = False
                    nat_client.send(data_bytes)
        except Exception as e:
            traceback.print_exc()


#一个服务一个进程
def init_process(config):
    print(config)
    pool = ThreadPoolExecutor(10)
    timeout = config['timeout']
    local_server_name = config['local_server_name']
    #注册服务
    while True:
        nat_client = register_nat_keepalive_connect(config)
        print('client : {0}'.format(nat_client))
        if not nat_client:
            #注册失败30秒后重试
            time.sleep(30)
            #注册失败
            continue
        try:
            rs,ws,es = select.select([nat_client],[],[])
            for sock in rs:
                print(sock.recv(1024))
                #pool.submit(server_handler,nat_client,timeout)
        except Exception as e:
            traceback.print_exc()
    if local_server_name in alive_processs.keys():
        del alive_processs[local_server_name]

def inspect_process():

    while True:
        time.sleep(10)
        if not alive_processs:
            continue
        for local_server_name in nat_config.keys():
            if local_server_name not in alive_processs.keys():
                config = nat_clients[local_server_name]
                p = process.Process(target=init_process,args=(config,))
                p.start()
                alive_processs[local_server_name] = p;
        
            
def start():
    #加载配置文件
    load_config()
    #初始化所有进程

    for local_server_name in nat_config.keys():
        print(local_server_name)
        config = nat_config[local_server_name]
        p = process.Process(target=init_process,args=(config,))
        alive_processs[local_server_name] = p
    for p in alive_processs.values():
        p.start()
    #启动守护进程
    p = process.Process(target=inspect_process,args=())
    p.start()

def load_config():
    config_file = open('config.json','r')
    config = config_file.read()
    config_file.close()
    config_objs = json.loads(config)
    for conf in config_objs:
        nat_config[conf['local_server_name']] = conf


if __name__ == "__main__":
    start()