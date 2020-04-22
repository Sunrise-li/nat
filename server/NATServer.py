import socket
import select
from quque import Queue
from threading import Thread

class WorkerThread(Thread):
    def __init__(self,sock):
        self.sock       = sock
        self.task_queue = Queue(0xffffffff)
    def put_task(self):
        self.task_put.put(self.sock.recv(0xffffff))
    def get_task(self):
        return self.task_queue.get()
    def send(self,task):
        self.sock.send(task)





class NATProcess:
    def tcp_forword(self,server,client):
        server = server
        client = client
        activity = True
        read_list = [server,client]
        while activity:
            rs,ws,es = select.select(read_list,[],[])
            for sock in rs:
                if sock is client:
                    data = sock.recv(self.max_pkg_len)
                    server.sendAll(data)
                elif sock is server:
                    data = sock.recv(self.max_pkg_len)
                    client.sendAll(data)

    def __init__(self,nat_port = None,server_port=None):
        self.readable_sock      = []
        self.writeable_sock     = []
        self.error_sock         = []
        self.nat_client_sock    = None
        self.max_queue          = 0xffffffff
        self.task_queue         = Queue(self.max_queue)
        self.max_pkg_len        = 0xffffff
        self.init_server(server_port)
        self.init_nat_server(nat_port)
        self.readable_sock.append(self.server)
        #self.readable_sock.append(self.nat_server)

    def init_server(self,port):
        self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server.bind(('127.0.0.1',port))
        self.server.listen()
    
    def init_nat_server(self,port):
        self.nat_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server.bind('127.0.0.1',port)
        self.server.listen()
    def server_handler(self):
        while True:
            try:
                rs,ws,es = select.select(self.readable_sock,self.writeable_sock,self.error_sock)
                for r in rs:
                    if r is self.server:
                        client = self.server.accept(self.max_pkg_len)
                        self.task_queue.put(client)
            except Exception as e:
                print(e)
        
class NATServer:
    pass

