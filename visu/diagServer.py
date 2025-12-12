import json
import zmq
import threading
import time
import os
import configparser

cfg = configparser.ConfigParser()


class diagServer(threading.Thread):
    def __init__(self, 
                 address: str = "tcp://*:1110",
                 host: str = "localhost",
                 data: dict | None = None, 
                 name: str = "default"):
        '''
        Visu server made to transmit a dictionnay 'data' to any client sending '__GET__'
        to the server.

        To start the server, create an instance of the server and use the 'start' method
        to assing its own thread:
            serv = diagServer()
            serv.start()

        To update the dictionnary, use 'setData' method:
            serv.setData(newData)

        To close the server, use the 'stop' method:
            serv.stop()

        Args:
            address: (str)
                the server adress.
            
            host: (str)
                the host adress.

            data: (dict)
                the dictionnary to transmit.
            
            name: (str)
                the name gave to the server.
        '''
        
        super().__init__() # heritage from Thread
        self._address = address
        self.name = name
        self._host = host
        self._data = data or {}
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self._address)

        self._running = threading.Event()
        self._running.set()

    @property
    def address(self) -> str:
        '''
        property to avoid 'address' modification.
        '''
        return self._address

    @property
    def host(self):
        '''
        property to avoid 'host' modification.
        '''
        return self._host
    
    @property
    def data(self) -> dict:
        '''
        property to avoid 'data' direct modification.
        To modify the 'data', use 'setData'.
        '''
        return self._data
    
    @property
    def running(self):
        '''
        property to avoid 'running' modification.
        '''
        return self._running

    @property
    def addressForClient(self):
        '''
        property that return the 'address' for the client.
        'tcp://<IP server>:port'
        '''
        proto, rest = self.address.split("://")
        host, port = rest.split(":")

        if host == "*":         # if the server is listening everywhere
            host = self.host    # use the server host refered in the class
                                # else use the specific adress required by the server

        return f"{proto}://{host}:{port}"

    def setData(self, newData: dict) -> None:
        '''
        Set a new dictionary to transmit.
        '''
        self._data = newData

    def run(self) -> None:
        '''
        Function used while the server is running.
        The server is waiting to receive messages from clients.
        keywords are:
            '__GET__': transmit the dictionnay
            '__STOP__': stop the server
        '''
        print(f"[diagServer {self.name}] Running on {self.address}")

        while self._running.is_set():
            
            try:
                
                if self.socket.poll(100): # poll for 100 ms
                    message = self.socket.recv_string()
                    print(f"[diagServer] Received: '{message}'")
                    
                    # stop the thread on message '__STOP__'
                    if message == "__STOP__":
                        self.socket.send_string("stopping") # interrupt the loop
                        break
                    
                    # send the dictionnary on message '__GET__'
                    elif message == "__GET__":
                        response = json.dumps(self.data)
                        self.socket.send_string(response)

                else:
                    time.sleep(0.01) # wait 10 ms

            except zmq.error.ContextTerminated:
                break

        print(f"[diagServer {self.name}] Closing socket...")
        self.socket.close(0) # close the server
        self.context.term() # close the context
        print(f"[diagServer {self.name}] Stopped")

    def stop(self) -> None:
        """
        Proper way to stop the thread where the server is running.
        The function send a '__STOP__' message to the server,
        which then close itself. To do so, the function create
        a client that will send the message, wait for the server to
        stop and then close itself.
        """
        print("[diagServer] Stopping...")

        # create a client ZMQ
        ctx = zmq.Context()
        sock = ctx.socket(zmq.REQ)
        print(self.address)
        sock.connect(self.addressForClient)

        try:
            # try tp send '__STOP__' to the server
            sock.send_string("__STOP__")
            sock.recv_string()  # response is mandatory in REP
        except Exception as e:
            print(f"[diagServer {self.name}] Stop error:", e)

        sock.close(0) # close the client
        ctx.term() # close the client context

        self._running.clear() # update the flag
        self.join() # wait until the thrad terminates


if __name__ == "__main__":
    cfg.read("visu_diagServ/visu/confServer.ini")
    print(cfg.sections())

    print("cwd =", os.getcwd())
    print("exists:", os.path.exists("visu_diagServ/visu/confServer.ini"))

    host = cfg["diagServer"].get("serverHost")
    port = cfg["diagServer"].get("serverPort")

    address = f"tcp://*:{port}"
    data = {"hello": "world", "x": 42}
    print(f"host = {host}")
    print(f"port = {port}")
    print(f"address = {address}")

    server = diagServer(address=address, host=host, data=data)
    server.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
