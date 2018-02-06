
import requests, threading, socketserver, re, socket
from http.client import BadStatusLine  # Python 3.x

class EchoRequestHandler(socketserver.BaseRequestHandler):
    
    def handle(self):
        try:
            # Echo the back to the client
            data = self.request.recv(1024)
            # Don't worry about a status for now, just echo back.
            self.request.sendall(data)
            # Then parse it.
            self.parent.handler(data.decode('utf-8','ignore'))
        except (Exception) as err:
            self.parent.parent.logger.error("request_handler failed {0}".format(err), exc_info=True)
        return

class CameraREST():

    def __init__(self,parent):
        self.parent  = parent

    def start(self):
        self.myip    = self.get_network_ip('8.8.8.8')
        self.address = (self.myip, 0) # let the kernel give us a port
        self.parent.logger.debug("CameraREST: address={0}".format(self.address))
        eh = EchoRequestHandler
        eh.parent = self
        self.server  = socketserver.TCPServer(self.address, eh)
        self.parent.logger.info("CameraRestServer: Running on: %s:%s" % self.server.server_address)
        self.thread  = threading.Thread(target=self.server.serve_forever)
        #t.setDaemon(True) # don't hang on exit
        self.thread.start()

    def get_network_ip(self,rhost):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((rhost, 0))
        except:
            self.parent.logger.error("CameraRestServer:get_network_ip: Failed to open socket to " + rhost)
            return False
        rt = s.getsockname()[0]
        s.close()
        return rt

    def handler(self, data):
        self.parent.logger.debug("CameraRestServer:handler: Got {0}".format(data.strip()))
        match = re.match( r'GET /motion/(.*) ', data, re.I)
        if match:
            address = match.group(1)
            self.parent.motion(address,1)
        else:
            self.parent.logger.error("CameraRestServer:handler: Unrecognized socket server command: " + data)

