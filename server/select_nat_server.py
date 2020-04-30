#!/usr/bin/python3
import socket
import select
import threading
import json
import time
import traceback
import rsa 
import os
import queue
import sys
import multiprocessing as process
from snow_flake import SnowFlake
from concurrent.futures import ThreadPoolExecutor

#结束符
EOF = b'\r\n\r\n0000\r\n\r\n'
#是否启动ssh身份验证
authentication = True

buff_size = 0xffff

nat_clients = {}

server_processs = {}

snowFlake = SnowFlake()

pub_key_path = os.path.join(os.getenv('HOME'),'.ssh/pub_key')
f = open(pub_key_path)
pub_key = rsa.PublicKey.load_pkcs1(f.read())
f.close()


def start():
    port = sys.argv[1]

    print('port:{0}'.format(port))
    register_nat_client(int(port))


def rsa_encrypt(s):
    return rsa.encrypt(s.encode('utf8'),pub_key)

def register_nat_client(port):
    register_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    register_server.bind(('0.0.0.0',port))
    register_server.listen(10)
    print('开始监听 {0}'.format(port))
    while True:
        try:
            #等待客户端注册
            nat_client,addr = register_server.accept()
            print(addr)
            data_bytes = nat_client.recv(buff_size)
            print(data_bytes)
            #读取配置文件
            data = data_bytes.decode('utf8')
            config = json.loads(data)
            print(config)
            #验证身份
            id_auth = str(snowFlake.id())
            print(id_auth)
            #发送认证信息
            nat_client.send(rsa_encrypt(id_auth))
            #接受认证结果
            auth_res = nat_client.recv(buff_size).decode('utf8')
            print(auth_res)
            if auth_res == id_auth:
                nat_client.send('ok'.encode('utf8'))
                nat_port = config['nat_port']
                timeout = config['timeout']
                key = str(nat_port) 
                if key not in nat_clients.keys():
                    nat_clients[key] = queue.Queue()
                    nat_clients[key].put(nat_client)
                else:
                    nat_clients[key].put(nat_client)
                if key not in server_processs.keys():
                    p = process.Process(target=init_server_process,args=(nat_port,timeout,))
                    server_processs[key] = p
                    p.start()
        except Exception as e:
            traceback.print_exc()
def init_server_process(port,timeout):
    pool = ThreadPoolExecutor(10)
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.bind(('0.0.0.0',port))
    server.listen(20)
    key = str(port)
    while True:
        try:
            client,addr = server.accept()
            if key in nat_clients.keys():
                nat_client = nat_clients[key].get()
                pool.submit(tcp_forword,nat_client,client,timeout)
        except Exception as e:
            traceback.print_exc()

def tcp_forword(nat_client,client,timeout=60):

    print('--------开始数据转发---------')
    nat_client = nat_client
    client = client
    read_list = [nat_client,client]
    #sock 文件描述符
    nat_client_fd = nat_client.fileno()
    client_fd = client.fileno()
    activity = True
    while activity:
        try:
            rs,ws,es = select.select(read_list,[],[],timeout)
            if not rs and not ws and not es:
                activity = False
            for sock in rs:
                data = sock.recv(buff_size)
                if b'HEART' in data:
                    if sock.fileno == client_fd:
                        keep_alive = 'KEEPALIVE'.encode('utf8')
                        sock.send(keep_alive)
                    continue
                if sock.fileno() == nat_client_fd:
                    #收到nat client 的结束符关闭于客户端的连接
                    if EOF in data:
                        client.close()
                        activity = False
                        break
                    client.send(data)
                elif sock.fileno() == client_fd:
                    #客户端返回空数据表示连接结束
                    if not data:
                        activity = False
                        nat_client.send(EOF)
                        nat_client.close()
                        break
                    nat_client.send(data)
        except Exception as e:
            traceback.print_exc()


if __name__ == "__main__":
    start()