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
import getopt
import hashlib
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

pub_key = ''

#黑名单
black_ip = {}

#读取公钥
def init_pub_key(pub_key_path = None):
    global pub_key 
    if not pub_key_path:
        pub_key_path = os.path.join(os.getenv('HOME'),'.ssh/pub_key')
    f = open(pub_key_path)
    pub_key = rsa.PublicKey.load_pkcs1(f.read())
    f.close()

def sha256(s):
    return hashlib.sha256(s.encode('utf8')).hexdigest()


def rsa_encrypt(s):
    return rsa.encrypt(s.encode('utf8'),pub_key)

def get_args():
    argv = sys.argv[1:]
    listen_port = None
    pub_key_path = None
    try:
        opts,args = getopt.getopt(argv,'hl:k:',['--listen=','--pub-key='])
        for opt,arg in opts:
            if opt == '-h':
                print("nat_server -l <listen-port> -k <pub-key> ")
                sys.exit()
            if opt in('-l','--listen'):
                listen_port = arg
            if opt in('-k','--pub-key'):
                pub_key_path = arg
        return (listen_port,pub_key_path)
    except getopt.GetoptError as e:
        print("nat_server -l <listen-port> -k <pub-keyy> ")
        sys.exit()

def register_nat_client(port):
    if not port:
        port = '8011'
    register_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    register_server.bind(('0.0.0.0',int(port)))
    register_server.listen(10)
    log.info('nat-register server listen port {0}'.format(port))
    while True:
        try:
            #等待客户端注册
            nat_client,addr = register_server.accept()
            #10次认证失败
            if black_ip[addr[0]]:
                nat_client.close()
                continue
            print('start register client {0}:{1}'.format(addr[0],addr[1]))
            data_bytes = nat_client.recv(buff_size)
            #读取配置文件
            data = data_bytes.decode('utf8')
            config = json.loads(data)
            server_name = config['server_name']
            signature =config['signature']
            del config['signature']
            if signature != sha256(json.dumps(config)):
                log.error('client {0}:{1} request falsify'.format(addr[0],addr[1]))
                nat_client.close()
            log.info(config)
            #验证身份
            id_auth = str(snowFlake.id())
            #发送认证信息
            nat_client.send(rsa_encrypt(id_auth))
            #接受认证结果
            auth_res = nat_client.recv(buff_size).decode('utf8')
            if auth_res == id_auth:
                nat_client.send('ok'.encode('utf8'))
                nat_port = config['nat_port']
                timeout = config['timeout']
                thread_pool_num = ['thread_pool_num']
                key = str(nat_port) 
                if key not in nat_clients.keys():
                    nat_clients[key] = Manager().Queue(10)
                    nat_clients[key].put(nat_client)
                else:
                    nat_clients[key].put(nat_client)
                if key not in server_processs.keys():
                    log.info('init {0} process'.format(server_name))
                    p = Process(target=init_server_process,args=(server_name,nat_clients[key],nat_port,thread_pool_num,timeout,))
                    server_processs[key] = p
                    p.start()
                    log.info('start {0} process'.format(server_name))
                    log.info('client {0}:{1}  register success'.format(addr[0],addr[1]))
            else:
                #认证失败
                if addr[0] in black_ip.keys():
                    black_ip[addr[0]] = black_ip[addr[0]]+1
                else:
                    black_ip[addr[0]] = 1
                nat_client.close()
                log.info('client {0}:{1}  register failed.'.format(addr[0],addr[1]))
        except Exception as e:
            log.error(traceback.format_exc())
def init_server_process(server_name,nat_client_queue,port,thread_pool_num=10,timeout=60):
    log.info('{0} process thread-pool-num {1}'.format(server_name,thread_pool_num))
    pool = ThreadPoolExecutor(thread_pool_num)
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.bind(('0.0.0.0',port))
    server.listen(20)
    log.info('{0} process listen {1}'.format(server_name,port))
    key = str(port)
    while True:
        try:
            client,addr = server.accept()
            client_addrs[client] = addr
            nat_client = nat_client_queue.get_nowait()
            pool.submit(tcp_forword,server_name,nat_client,client,timeout)
        except Exception as e:
            log.error(traceback.format_exc())

def tcp_forword(server_name,nat_client,client,timeout=60):
    log.info('tcp-forword...')
    nat_client = nat_client
    client = client
    #sock 文件描述符
    nat_client_fd = nat_client.fileno()
    client_fd = client.fileno()
    activity = True
    server_name = server_name
    client_ip,client_port = client_addrs[client]
    read_list = [client,nat_client]
    while activity:
        try:
            print(read_list)
            rs,ws,es = select.select(read_list,[],[],timeout)
            if not rs and not ws and not es:
                activity = False
                break
            for sock in rs:
                data = sock.recv(buff_size)
                #心跳包
                if b'HEART' in data:
                    if sock.fileno == client_fd:
                        keep_alive = 'KEEPALIVE'.encode('utf8')
                        sock.send(keep_alive)
                    continue
                if not data:
                    activity = False
                    break
                if sock.fileno() == nat_client_fd:
                    #收到nat client 的结束符关闭于客户端的连接
                    client.send(data)
                elif sock.fileno() == client_fd:
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
    listen_port,pub_key_path = get_args()
    init_pub_key(pub_key_path)
    register_nat_client(listen_port)
    

if __name__ == "__main__":
    start()