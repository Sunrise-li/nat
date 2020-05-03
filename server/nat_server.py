#!/usr/bin/python3
import socket
import select
import threading
import json
import time
import traceback
import rsa 
import os
# import queue
import sys
import logging as log
from snow_flake import SnowFlake
from multiprocessing import Process,Queue,Manager
from concurrent.futures import ThreadPoolExecutor

log.basicConfig(format='%(asctime)s - pid:%(process)d - tid:%(thread)d - [line:%(lineno)d] - %(levelname)s: %(message)s',level=log.INFO)


#结束符
EOF = b'\r\n\r\n0000\r\n\r\n'
#是否启动ssh身份验证
authentication = True

buff_size = 0xffff

queue_max_size = 0xffff

nat_clients = {}

server_processs = {}

client_addrs = {}

nat_client_addrs = {}

snowFlake = SnowFlake()

#读取公钥
def init_pub_key(pub_key_path = None):
    if not pub_key_path:
        pub_key_path = os.path.join(os.getenv('HOME'),'.ssh/pub_key')
    f = open(pub_key_path)
    pub_key = rsa.PublicKey.load_pkcs1(f.read())
    f.close()
    return pub_key

def tcp_forword(server_name,nat_client,client,timeout=60):
    log.info('start tcp-forword...')
    nat_client = nat_client
    client = client
    #sock 文件描述符

    nat_client_fd = nat_client.fileno()
    client_fd = client.fileno()
    activity = True
    server_name = server_name
    client_ip,client_port = client_addrs[client]
    #data = client.recv(buff_size)
    #print('client-first-data {0}'.format(data))
    #nat_client.send(data)
    read_list = [nat_client,client]
    while activity:
        try:
            rs,ws,es = select.select(read_list,[],[],timeout)
            if not rs and not ws and not es:
                activity = False
                break
            for sock in rs:
                data = sock.recv(buff_size)
                if b'HEART' in data:
                    if sock.fileno == client_fd:
                        keep_alive = 'KEEPALIVE'.encode('utf8')
                        sock.send(keep_alive)
                    continue
                if not data:
                    activity = False
                    break
                if sock.fileno() == nat_client_fd:
                    #log.info('client-host {0}:{1} send data to {2} service.'.format(client_ip,client_port,server_name))
                    #print('nat_client_fd {0}'.format(data))
                    #收到nat client 的结束符关闭于客户端的连接
                    client.send(data)
                elif sock.fileno() == client_fd:
                    #log.info('{0} service revert data to {1}:{2}'.format(server_name,client_ip,client_port))
                    #print('client_fd {0}'.format(data))
                    #客户端返回空数据表示连接结束
                    nat_client.send(data)
        except Exception as e:
            activity = False
            log.error(traceback.format_exc())
    
    nat_client.send(EOF)
    nat_client.close()
    client.close()
    del client_addrs[client]
    
    log.info('client {0}:{1} to {2} service connect closed.'.format(client_ip,client_port,server_name))


def start():
    port = sys.argv[1]
    register_nat_client(int(port))


def rsa_encrypt(s,pub_key):
    return rsa.encrypt(s.encode('utf8'),pub_key)

def register_nat_client(port):
    register_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    register_server.bind(('0.0.0.0',port))
    register_server.listen(10)
    log.info('nat-register service listen port {0}'.format(port))
    #读取公钥
    pub_key = init_pub_key()
    while True:
        try:
            #等待客户端注册
            nat_client,addr = register_server.accept()
            print('start register client {0}:{1}'.format(addr[0],addr[1]))
            data_bytes = nat_client.recv(buff_size)
            #读取配置文件
            data = data_bytes.decode('utf8')
            config = json.loads(data)
            server_name = config['server_name']
            log.info(config)
            log.info('start authentication...')
            #验证身份
            id_auth = str(snowFlake.id())
            #发送认证信息
            log.info('send to auth info.')
            nat_client.send(rsa_encrypt(id_auth,pub_key))
            #接受认证结果
            auth_res = nat_client.recv(buff_size).decode('utf8')
            if auth_res == id_auth:
                nat_client.send('ok'.encode('utf8'))
                nat_port = config['nat_port']
                timeout = config['timeout']
                key = str(nat_port) 
                if key not in nat_clients.keys():
                    nat_clients[key] = Manager().Queue(10)
                    nat_clients[key].put(nat_client)
                else:
                    nat_clients[key].put(nat_client)
                if key not in server_processs.keys():
                    log.info('init {0} service process'.format(server_name))
                    p = Process(target=init_server_process,args=(server_name,nat_clients[key],nat_port,timeout,))
                    server_processs[key] = p
                    p.start()
                    log.info('start {0} service process'.format(server_name))
                    log.info('client {0}:{1}  register success'.format(addr[0],addr[1]))
            else:
                nat_client.close()
                log.info('client {0}:{1}  register failed.'.format(addr[0],addr[1]))
        except Exception as e:
            log.error(traceback.format_exc())
def init_server_process(server_name,nat_client_queue,port,timeout):
    log.info('{0} service process thread-pool-num {1}'.format(server_name,timeout))
    pool = ThreadPoolExecutor(10)
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.bind(('0.0.0.0',port))
    server.listen(20)
    log.info('{0} service process listen {1}'.format(server_name,port))
    key = str(port)
    while True:
        try:
            client,addr = server.accept()
            client_addrs[client] = addr
            # print('data {0}'.format(client.recv(buff_size)))
            nat_client = nat_client_queue.get()
            pool.submit(tcp_forword,server_name,nat_client,client,timeout)
        except Exception as e:
            log.error(traceback.format_exc())

if __name__ == "__main__":
    start()