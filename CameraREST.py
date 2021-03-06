
import requests, threading, socketserver, re, socket
from camera_funcs import get_network_ip
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
        self.myip    = self.get_network_ip()
        if self.myip is False:
            self.parent.logger.error('CameraREST: Unable to start since')
            return False
        self.address = (self.myip, 0) # let the kernel give us a port
        self.parent.logger.debug("CameraREST: address={0}".format(self.address))
        eh = EchoRequestHandler
        eh.parent = self
        self.server  = socketserver.TCPServer(self.address, eh)
        self.parent.logger.info("CameraREST: Running on: %s:%s" % self.server.server_address)
        self.thread  = threading.Thread(target=self.server.serve_forever)
        #t.setDaemon(True) # don't hang on exit
        self.thread.start()

    def get_network_ip(self):
        """
        Return the/a network-facing IP number for this system.
        """
        return get_network_ip(self.parent.logger)

    def handler(self, data):
        self.parent.logger.debug("CameraRestServer:handler: Got {0}".format(data.strip()))
        match = re.match( r'GET /motion/(.*) ', data, re.I)
        if match:
            address = match.group(1)
            self.parent.motion(address,1)
        else:
            self.parent.logger.error("CameraRestServer:handler: Unrecognized socket server command: " + data)
