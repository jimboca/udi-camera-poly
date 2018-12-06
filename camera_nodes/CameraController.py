
import polyinterface
import os, json, logging, requests, threading,  re, socket, yaml
# SocketServer,
from requests.auth import HTTPDigestAuth,HTTPBasicAuth
from http.client import BadStatusLine  # Python 3.x
from foscam_poll import foscam_poll
from camera_nodes import *
from camera_funcs import myint,long2ip,get_server_data
from CameraREST import CameraREST

LOGGER = polyinterface.LOGGER

class CameraController(polyinterface.Controller):
    """
    The Controller Class is the primary node from an ISY perspective. It is a Superclass
    of polyinterface.Node so all methods from polyinterface.Node are available to this
    class as well.

    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot for the controller Node
    self.added: Boolean Confirmed added to ISY as primary node
    self.config: Dictionary, this node's Config

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node, update = False): Adds Node to self.nodes and polyglot/ISY. This is called
        for you on the controller itself. Update = True overwrites the existing Node data.
    updateNode(polyinterface.Node): Overwrites the existing node data here and on Polyglot.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    getDriver('ST'): gets the current value from Polyglot for driver 'ST' returns a STRING, cast as needed
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """
    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
        self.serverdata = get_server_data(LOGGER)
        self.l_info('init','Initializing VERSION=%s' % (self.serverdata['version']))
        super(CameraController, self).__init__(polyglot)
        self.name = 'Camera Controller'
        self.address = 'cameractrl'
        # I am my own primary
        self.primary = self.address

    def start(self):
        """
        Optional.
        Polyglot v2 Interface startup done. Here is where you start your integration.
        This will run, once the NodeServer connects to Polyglot and gets it's config.
        In this example I am calling a discovery method. While this is optional,
        this is where you should start. No need to Super this method, the parent
        version does nothing.
        """
        self.l_info('start',"...")
        # TODO; This is only necessary when drivers change?
        #self.addNode(self,update=True)
        self.discover_thread = None
        self.num_cams       = self.getDriver('GV3')
        self.foscam_polling = self.getDriver('GV4')
        self.debug_mode     = self.getDriver('GV5')
        self.hb             = 0

        # Short Poll
        val = self.getDriver('GV6')
        self.l_debug("start","shortPoll={0} GV6={1}".format(self.polyConfig['shortPoll'],val))
        if val is None or int(val) == 0:
            val = self.polyConfig['shortPoll']
            self.setDriver('GV6',val)
        else:
            self.polyConfig['shortPoll'] = int(val)
        self.short_poll = val

        # Long Poll
        val = self.getDriver('GV7')
        self.l_debug("start","longPoll={0} GV7={1}".format(self.polyConfig['longPoll'],val))
        if val is None or int(val) == 0:
            val = self.polyConfig['longPoll']
            self.setDriver('GV7',val)
        else:
            self.polyConfig['longPoll'] = int(val)
        self.long_poll = val

        self.logger = LOGGER
        self.rest_server = CameraREST(self)
        self.rest_server.start()

        self.query();
        self.load_params()
        self.add_all_cams()

    def shortPoll(self):
        """
        Optional.
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        if self.discover_thread is not None:
            if self.discover_thread.isAlive():
                self.l_debug('shortPoll','discover thread still running...')
            else:
                self.l_debug('shortPoll','discover thread is done...')
                self.discover_thread = None
        for node in self.nodes:
            if self.nodes[node].address != self.address:
                self.nodes[node].shortPoll()

    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        self.heartbeat()
        pass

    def query(self):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
        self.setDriver('GV1', self.serverdata['version_major'])
        self.setDriver('GV2', self.serverdata['version_minor'])
        self.set_num_cams(self.num_cams)
        self.set_foscam_polling(self.foscam_polling)
        self.set_debug_mode(self.debug_mode)
        self.set_short_poll(self.short_poll)
        self.set_long_poll(self.long_poll)
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def heartbeat(self):
        self.l_debug('heartbeat','hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def discover(self, *args, **kwargs):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command recieved from ISY as an exmaple.
        """
        if self.load_params():
            self.l_info("discover","Refuse to continue since load_params failed")
        if self.foscam_polling > 0:
            self.discover_foscam()
        else:
            self.l_info("discover","Not Polling for Foscam MJPEG cameras %s" % (self.foscam_polling))
            self.set_num_cams(self.num_cams)
        self.l_info('discover',"Done adding cameras")

    def delete(self):
        """
        Example
        This is sent by Polyglot upon deletion of the NodeServer. If the process is
        co-resident and controlled by Polyglot, it will be terminiated within 5 seconds
        of receiving this message.
        """
        self.l_info('delete','Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def get_node(self,address):
        self.l_info('get_node',"adress={0}".format(address))
        for node in self.nodes:
            #self.l_debug('get_node',"node={0}".format(node))
            if self.nodes[node].address == address:
                return self.nodes[node]
        return None

    def load_params(self):
        """
        Load the user defined params
        user = The user name to log into cameras
        password = And the matching password
        """
        st = True
        default_user = "YourCameraUserName"
        default_password = "YourCameraPassword"

        if 'user' in self.polyConfig['customParams']:
            self.user = self.polyConfig['customParams']['user']
        else:
            self.l_error('load_params',"user not defined in customParams, please add it.  Using admin")
            self.user = default_user
            st = False

        if 'password' in self.polyConfig['customParams']:
            self.password = self.polyConfig['customParams']['password']
        else:
            self.l_error('load_params',"password not defined in customParams, please add it.  Using admin")
            self.password = default_password
            st = False

        # Make sure they are in the params
        self.addCustomParam({'password': self.password, 'user': self.user, 'cam_example': '{ "type": "Amcrest", "host": "host_or_IP", "port": "port_number" }'})

        self.removeNoticesAll()
        if self.user == default_user or self.password == default_password:
            self.addNotice("Please set proper camera user and password in Configuration page, and restart this nodeserver")

    def add_all_cams(self):
        self.set_num_cams(0)
        self.add_existing_cams()
        self.add_config_cams()

    def add_existing_cams(self):
        """
        Called on startup to add the cameras from the config
        """
        for address in self._nodes:
            node = self._nodes[address]
            self.l_info("add_existing_cams","node={0} = {1}".format(address,node))
            if node['address'] == self.address:
                # Ignore myself
                pass
            elif node['node_def_id'] == "FoscamMJPEG":
                self.l_info("add_existing_cams","Adding FoscamMJPEG camera: %s" % (node['name']))
                self.addNode(FoscamMJPEG(self, self.user, self.password, node_data=node))
                self.incr_num_cams()
            elif node['node_def_id'] == "FoscamHD2":
                self.l_info("add_existing_cams","Adding FoscamHD2 camera: {0} = {1}".format(node['name'],node))
                self.addNode(FoscamHD2(self, self.user, self.password, node_data=node))
                self.incr_num_cams()
            elif node['node_def_id'] == 'CamMotion':
                pass
            else:
                self.l_error("add_existing_cams","Unknown camera id %s for %s" % (node['node_def_id'],node['name']))

    def add_config_cams(self):
        """
        Add cameras defined in customParams
        """
        for param in self.polyConfig['customParams']:
            # Look for customParam starting with cam_
            match = re.match( "cam_(.*)", param, re.I)
            if match is not None and match.group(1) != "example":
                # The hub address can be everything following the cam_
                address = match.group(1)
                self.l_info('add_config_cams','got param {0} {1}'.format(param,address))
                # Get the customParam value which is json code
                #  { "type":"Amcrest", "host": "192.168.1.86", "port": "80" }
                cfg = self.polyConfig['customParams'][param]
                try:
                    cfgd = json.loads(cfg)
                except:
                    err = sys.exc_info()[0]
                    self.l_error('add_config_cams','failed to parse cfg={0} Error: {1}'.format(cfg,err))
                # Check host and type are defined.
                addit = True
                if not 'host' in cfgd:
                    self.l_error('add_config_cams','No host in customParam {0} value={1}'.format(param,cfg))
                    addit = False
                if not 'type' in cfgd:
                    self.l_error('add_config_cams','No type in customParam {0} value={1}'.format(param,cfg))
                    addit = False
                if addit:
                    if cfgd['type'] == "Amcrest":
                        self.addNode(Amcrest(self, self.user, self.password, config=cfgd))
                    self.incr_num_cams()

    def discover_foscam(self):
        self.l_info("discover_foscam","Polling for Foscam cameras %s" % (self.foscam_polling))
        cams = foscam_poll(LOGGER)
        self.l_debug("discover_foscam","Camera Data: " + str(cams))
        for cam in cams:
            cam['id'] = cam['id'].lower()
            self.l_info("discover_foscam","Checking to add camera: id=%s name=%s" % (cam['id'], cam['name']))
            for key, value in cam.items():
                if key != 'name' and key != 'id':
                    self.l_debug('discover_foscam','  {}={}'.format(key,value))
            lnode = self.get_node(cam['id'])
            if lnode:
                self.l_info("discover_foscam","Already exists, updating %s %s" % (cam['id'], cam['name']))
                lnode.update_config(self.user, self.password, udp_data=cam)
                lnode.update_drivers()
            else:
                if cam['mtype'] == "MJPEG":
                    self.l_info("discover_foscam","Adding FoscamMJPEG camera: %s" % (cam['name']))
                    self.addNode(FoscamMJPEG(self, self.user, self.password, udp_data=cam))
                    self.incr_num_cams()

                elif cam['mtype'] == "HD2":
                    self.l_info("discover_foscam","Adding FoscamHD camera: %s" % (cam['name']))
                    self.addNode(FoscamHD2(self, self.user, self.password, udp_data=cam))
                    self.incr_num_cams()

                else:
                    self.l_error("discover_foscam","Unknown type %s for Foscam Camera %s" % (cam['type'],cam['name']))
            self.l_info("discover_foscam","Done")

    def on_exit(self, **kwargs):
        self.server.socket.close()
        return True

    def motion(self,address,value):
        """ Poll Camera's  """
        self.l_info("motion","%s '%s'" % (address, value) )
        lnode = self.get_node(address)
        if lnode:
            return lnode.motion(value)
        else:
            self.l_error("motion","No node for motion on address %s" % (address));
        return False

    def http_get(self,ip,port,user,password,path,payload,auth_mode=0):
        url = "http://{}:{}/{}".format(ip,port,path)

        payload_mask = payload
        payload_mask['pwd'] = '*'
        self.l_debug("http_get","Sending: %s %s auth_mode=%d" % (url, payload, auth_mode) )
        if auth_mode == 0:
            auth = HTTPBasicAuth(user,password)
        elif auth_mode == 1:
            auth = HTTPDigestAuth(user,password)
        else:
            self.l_error('http_get',"Unknown auth_mode '%s' for request '%s'.  Must be 0 for 'digest' or 1 for 'basic'." % (auth_mode, url) )
            return False

        try:
            response = requests.get(
                url,
                auth=auth,
                params=payload,
                timeout=5
            )
        # This is supposed to catch all request excpetions.
        except requests.exceptions.RequestException as e:
            self.l_error('http_get',"Connection error for %s: %s" % (url, e))
            return False
        self.l_debug('http_get',' Got: code=%s text=%s' % (response.status_code,response.text))
        if response.status_code == 200:
            #self.l_debug('http_get',"http_get: Got: text=%s" % response.text)
            return response.text
        elif response.status_code == 400:
            self.l_error('http_get',"Bad request: %s" % (url) )
        elif response.status_code == 404:
            self.l_error('http_get',"Not Found: %s" % (url) )
        elif response.status_code == 401:
            # Authentication error
            self.l_error('http_get',
                "Failed to authenticate, please check your username and password")
        else:
            self.l_error('http_get',"Unknown response %s: %s" % (response.status_code, url) )
        return False

    def l_info(self, name, string):
        LOGGER.info("%s:%s: %s" %  (self.id,name,string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s: %s" % (self.id,name,string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s: %s" % (self.id,name,string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s: %s" % (self.id,name,string))

    def set_num_cams(self,val):
        if val is None:
            val = 0
        self.num_cams = int(val)
        self.setDriver('GV3',self.num_cams)

    def incr_num_cams(self):
        self.set_num_cams(self.num_cams + 1)

    def set_foscam_polling(self,val):
        if val is None:
            val = 0
        self.foscam_polling = int(val)
        self.setDriver('GV4', self.foscam_polling)

    def set_debug_mode(self,level):
        if level is None:
            level = 0
        else:
            level = int(level)
        self.debug_mode = level
        self.setDriver('GV5', self.debug_mode)
        if level == 0 or level == 10:
            self.set_all_logs(logging.DEBUG)
        elif level == 20:
            self.set_all_logs(logging.INFO)
        elif level == 30:
            self.set_all_logs(logging.WARNING)
        elif level == 40:
            self.set_all_logs(logging.ERROR)
        elif level == 50:
            self.set_all_logs(logging.CRITICAL)
        else:
            self.l_error("set_debug_mode","Unknown level {0}".format(level))

    def set_all_logs(self,level):
        LOGGER.setLevel(level)
        logging.getLogger('requests').setLevel(level)
        logging.getLogger('urllib3').setLevel(level)

    def set_short_poll(self,val):
        if val is None:
            val = 0
        self.short_poll = int(val)
        self.setDriver('GV6', self.short_poll)
        self.polyConfig['shortPoll'] = val

    def set_long_poll(self,val):
        if val is None:
            val = 0
        self.long_poll = int(val)
        self.setDriver('GV7', self.long_poll)
        self.polyConfig['longPoll'] = val

    def cmd_install_profile(self,command):
        self.l_info("cmd_install_profile","installing...")
        self.poly.installprofile()

    def cmd_set_foscam_polling(self,command):
        """ Enable/Disable Foscam UDP Searching
              0 = Off
              1 = 10 second query
              2 = 20 second query
              3 = 30 second query
              4 = 60 second query
        """
        val = int(command.get('value'))
        self.l_info("cmd_set_foscam_polling",val)
        self.set_foscam_polling(val)

    def cmd_set_debug_mode(self,command):
        val = command.get('value')
        self.l_info("cmd_set_debug_mode",val)
        self.set_debug_mode(val)

    def cmd_set_short_poll(self,command):
        val = command.get('value')
        self.l_info("cmd_set_short_poll",val)
        self.set_short_poll(val)

    def cmd_set_long_poll(self,command):
        val = int(command.get('value'))
        self.l_info("cmd_set_long_poll",val)
        self.set_long_poll(val)

    """
    Optional.
    Since the controller is the parent node in ISY, it will actual show up as a node.
    So it needs to know the drivers and what id it will use. The drivers are
    the defaults in the parent Class, so you don't need them unless you want to add to
    them. The ST and GV1 variables are for reporting status through Polyglot to ISY,
    DO NOT remove them. UOM 2 is boolean.
    """
    id = 'CameraController'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'INSTALL_PROFILE': cmd_install_profile,
        'SET_FOSCAM_POLLING': cmd_set_foscam_polling,
        'SET_DM': cmd_set_debug_mode,
        'SET_SHORTPOLL': cmd_set_short_poll,
        'SET_LONGPOLL':  cmd_set_long_poll
    }
    drivers = [
        {'driver': 'ST',  'value': 1, 'uom': 2},
        {'driver': 'GV1', 'value': 0, 'uom': 56}, # Major version of this code.
        {'driver': 'GV2', 'value': 0, 'uom': 56}, # Minor version of this code.
        {'driver': 'GV3', 'value': 0, 'uom': 56}, # Number of cameras we manage
        {'driver': 'GV4', 'value': 1, 'uom': 25}, # Foscam Polling
        {'driver': 'GV5', 'value': 0, 'uom': 25}, # Debug (Log) Mode
        {'driver': 'GV6', 'value': 5, 'uom': 25}, # shortpoll
        {'driver': 'GV7', 'value': 60, 'uom': 25}  # longpoll
    ]
