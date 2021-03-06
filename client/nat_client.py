#!/usr/bin/python3
import socket
import select
import threading
import json
import time
import rsa 
import os
import sys
import getopt
import hashlib
import traceback
import multiprocessing as process
import logging as log
from concurrent.futures import ThreadPoolExecutor 
from concurrent.futures import ThreadPoolExecutor

log.basicConfig(format='%(asctime)s - pid:%(process)d - tid:%(thread)d - [line:%(lineno)d] - %(levelname)s: %(message)s',level=log.INFO)
#配置文件
nat_config = {}
#nat服务 文件描述符  和本地服务地址映射 用于多服务注册转发
nat_client_fd_local_server = {}


#内网穿透sock 负责和服务器建立长连接转发数据包
nat_clients = {}
priv_key = ''



buff_size = 0xffff

EOF = b'\r\n\r\n0000\r\n\r\n'
#活动中的进程
alive_processs = {}
def get_args():
    argv = sys.argv[1:]
    config_path = ''
    priv_key_path = ''
    try:
        opts,args = getopt.getopt(argv,'hc:k:',['--config=','--priv-key='])
        for opt,arg in opts:
            if opt == '-h':
                print("nat_client -c <config-file> -k <priv-key> ")
                sys.exit()
            if opt in('-c','--config'):
                config_path = arg
            if opt in('-k','--priv-key'):
                priv_key_path = arg
        return (config_path,priv_key_path)
    except getopt.GetoptError as e:
        print("nat_client -c <config-file> -k <priv_key> ")
        sys.exit()

#初始化全局配置
def init_config(config_path = None):
    if not config_path:
        config_path = 'config.json'
    config_file = open(config_path,'r')
    config = config_file.read()
    config_file.close()
    config_objs = json.loads(config)
    for conf in config_objs:
        nat_config[conf['local_server_name']] = conf

#rsa 配置私钥
def init_priv_key(priv_key_path = None):
    global priv_key
    if not priv_key_path:
        priv_key_path = os.path.join(os.getenv('HOME'),'.ssh/priv_key')
    f = open(priv_key_path)
    priv_key = rsa.PrivateKey.load_pkcs1(f.read())
    f.close()

#每10秒检查并启动出错而关闭的服务
def daemon_process():
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


#心跳测试 检查服务状态 如有异常停止服务 等待守护进程重启
def inspect_server():
    while True:
        for server_name in nat_config.keys():
            config = nat_config[server_name]
            ip = config['local_server_ip']
            port = config['local_server_port']
            heart = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            try:
                heart.settimeout(3)
                heart.connect((ip,port))
                heart.close()
            except Exception as e:
                heart.close()
                log.error(traceback.format_exc())
                alive_processs[server_name].kill()
                del alive_processs[server_name]
        time.sleep(30)

#和公网服务器创建长连接
def register_nat_keepalive_connect(config):
   
    try:
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
        #处理线程池大小
        thread_pool_num         = config['thread_pool_num']
        server_addr = '{0}:{1}'.format(net_server_ip,nat_server_port)
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        log.info('start registration service {0} - {1}:{2} remote host {3}:{4}'.format(local_server_name,local_server_ip,local_server_port,net_server_ip,nat_server_port))
        sock.connect((net_server_ip,register_server_port))
        #ssh:8022
        data = {
            'server_name':local_server_name,
            'timeout':timeout,
            'nat_port':nat_server_port,
            'thread_pool_num':thread_pool_num
        }
         #数字签名
        signature = hashlib.sha256(json.dumps(data).encode('utf8')).hexdigest()
        data['signature'] = signature

        #向服务端发送注册信息
        data_bytes= json.dumps(data).encode('utf8')
        #发送注册信息
        log.info('start authentication ....')
        sock.send(data_bytes)
        id_auth = sock.recv(buff_size)
        #身份验证
        auth = rsa_decrypt(id_auth);
        sock.send(auth)
        auth_res = sock.recv(buff_size)
        if b'ok' in auth_res:
            #注册服务
            nat_clients[server_addr] = sock
            sock_fd = sock.fileno()
            if sock_fd in nat_client_fd_local_server.keys():
                del nat_client_fd_local_server[sock_fd]
            nat_client_fd_local_server[sock_fd] = '{0}:{1}'.format(local_server_ip,local_server_port)
            log.info('registration server {0} success.'.format(local_server_name))
            return sock
        else:
            log.error('registration failed server {0} to remote host {1}:{2}'.format(local_server_name,net_server_ip,nat_server_port))
            sock.close()
    except Exception as e:
        log.error(traceback.format_exc())
    return None

def rsa_decrypt(ciphertext):
    return rsa.decrypt(ciphertext,priv_key)

#创建本地服务连接
#本地服务IP local_server_ip
#本地服务监听端口  local_server_port
def create_local_server_connect(local_server_ip,local_server_port,keep_alive=False):
    local_server_addr = '{0}:{1}'.format(local_server_ip,local_server_port)
    log.info('create local server addr {0}'.format(local_server_addr))
    try:
        local_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        if keep_alive:
            #长连接
            local_server.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
        local_server.connect((local_server_ip,local_server_port))
        log.info('connect addr {0} success.'.format(local_server_addr))
        return local_server
    except Exception as e:
        log.error(traceback.format_exc())
    log.error('connect addr {0} failed.'.format(local_server))
    return None
    
#处理用户情求 默认超时时间1分钟
def server_handler(nat_client,timeout=69):
    log.info('start excution client requests.')
    nat_client = nat_client
    #nat_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    nat_client_fd = nat_client.fileno()
    if nat_client_fd not in nat_client_fd_local_server.keys():
        return 
    #通过nat 客户端文教描述符取出对应本地服务地址
    local_server_addr = nat_client_fd_local_server[nat_client_fd];
    log.info('access {0}'.format(local_server_addr))
    #解析地址
    local_server_ip_port = local_server_addr.split(':')
    local_server_ip = local_server_ip_port[0]
    local_server_port = local_server_ip_port[1]
    #获取本地连接
    local_server = create_local_server_connect(local_server_ip,int(local_server_port))
    if not local_server:
        return 
    log.info('connected {0} '.format(local_server_addr))
    local_server_fd = local_server.fileno()
    activity = True
    read_list = [nat_client,local_server]
    while activity:
        try:
            rs,ws,es = select.select(read_list,[],[],timeout)
            for sock in rs:
                data_bytes = sock.recv(buff_size)
                #将数据转发对方
                #没有数据 结束当前会话
                if not data_bytes:
                    local_server.close()
                    nat_client.close()
                    activity = False
                if sock.fileno() == nat_client_fd:
                    #收到结束符关闭连接
                    local_server.send(data_bytes)
                elif sock.fileno() == local_server_fd:
                    nat_client.send(data_bytes)
        except Exception as e:
            local_server.close()
            nat_client.close()
            activity = False
            log.error(traceback.format_exc())
    del nat_clients[local_server_addr]
#一个服务一个进程
def init_process(config):
    pool = ThreadPoolExecutor(10)
    timeout = config['timeout']
    local_server_name = config['local_server_name']
    #注册服务
    while True:
        nat_client = register_nat_keepalive_connect(config)
        if not nat_client:
            log.error('registration failed wait 30s repeat')
            #注册失败30秒后重试
            time.sleep(10)
            #注册失败
            continue
        try:
            rs,ws,es = select.select([nat_client],[],[])
            for sock in rs:
                pool.submit(server_handler,nat_client,timeout)
        except Exception as e:
            traceback.print_exc()
    if local_server_name in alive_processs.keys():
        del alive_processs[local_server_name]

def start():
    #解析命令行参数
    config_path,priv_key_path = get_args()
    #初始化私钥
    init_priv_key(priv_key_path)
    #初始化全局配置
    init_config(config_path)
    #初始化所有进程
    for local_server_name in nat_config.keys():
        config = nat_config[local_server_name]
        p = process.Process(target=init_process,args=(config,))
        alive_processs[local_server_name] = p
    for p in alive_processs.values():
        p.start()
    #监听服务器状态
    inspect = process.Process(target=inspect_server,args=())
    inspect.start()
    #启动守护进程
    daemon = process.Process(target=daemon_process,args=())
    daemon.start()

if __name__ == "__main__":
    start()