
import requests, threading, SocketServer, re, socket
from http.client import BadStatusLine  # Python 3.x


class EchoRequestHandler(SocketServer.BaseRequestHandler):
    
    def handle(self,parent):
        self.parent = parent
        try:
            # Echo the back to the client
            data = self.request.recv(1024)
            # Don't worry about a status for now, just echo back.
            self.request.sendall(data)
            # Then parse it.
            parent.handler(data)
        except:
            logger.error("request_handler failed")
        return

class CameraRestServer():

    def __init__(self,parent):
        self.parent  = parent

    def start():
        self.myip    = self.get_network_ip('8.8.8.8')
        self.address = (myip, 0) # let the kernel give us a port
        self.server  = SocketServer.TCPServer(self.address, EchoRequestHandler(self))
        self.parent.logger.info("CameraRestServer: Running on: %s:%s" % server.server_address)
        self.thread  = threading.Thread(target=server.serve_forever)
        #t.setDaemon(True) # don't hang on exit
        self.thread.start()

    def get_network_ip(self,rhost):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((rhost, 0))
        except:
            self.parent.logger.error("CameraRestServer:get_network_ip: Failed to open socket to " + rhost)
            return False
        return s.getsockname()[0]

    def handler(data):
        self.parent.logger.debug("CameraRestServer:handler: Got {0}".format(data.strip()))
        match = re.match( r'GET /motion/(.*) ', data, re.I)
        if match:
            address = match.group(1)
            self.parent.motion(address,1)
        else:
            self.parent.logger.error("CameraRestServer:handler: Unrecognized socket server command: " + data)

