
import polyinterface
from foscam_poll import foscam_poll
from camera_nodes import *
from camera_funcs import myint,long2ip,get_server_data

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
        self.addNode(self,update=True)
        self.num_cams     = self.getDriver('GV3')
        self.foscam_mjpeg = self.getDriver('GV4')
        self.debug_mode   = self.getDriver('GV5')
        self.short_poll   = self.getDriver('GV6')
        self.long_poll    = self.getDriver('GV7')
        self.query();
        self.load_params()
        self.add_polyconfig_cams()
        self.add_config_cams()

    def shortPoll(self):
        """
        Optional.
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        pass

    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
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
        self.set_foscam_mjpeg(self.foscam_mjpeg)
        self.set_debug_mode(self.debug_mode)
        self.set_short_poll(self.short_poll)
        self.set_long_poll(self.long_poll)
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command recieved from ISY as an exmaple.
        """
        if self.foscam_mjpeg > 0:
            self.discover_foscam(manifest)
        else:
            self.l_info("discover","Not Polling for Foscam MJPEG cameras %s" % (self.foscam_mjpeg))
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

    def load_params(self):
        """
        Load the user defined params
        user = The user name to log into cameras
        passwrd = And the matching password
        """
        if 'user' in self.polyConfig['customParams']:
            self.user = self.polyConfig['customParams']['user']
        else:
            self.l_error('load_params',"user not defined in customParams, please add it.  Using admin")
            self.user = 'admin'
        if 'password' in self.polyConfig['customParams']:
            self.password = self.polyConfig['customParams']['password']
        else:
            self.l_error('load_params',"password not defined in customParams, please add it.  Using admin")
            self.password = 'admin'

    def add_polyconfig_cams(self):
        """
        Called on startup to add the cameras from the config
        """
        # TODO: Add code to loop over self.polyConfig["nodes"] ?
        pass

    def add_config_cams(self):
        """
        Add cameras defined in customParams
        """
        # Add cameras from our config
        #self.parent.logger.debug("CameraServer:add_config_cams: cameras=%s" % (config['cameras']))
        #for a_config in config['cameras']:
        #    if a_config['type'] == "Amcrest1":
        #        self.parent.logger.debug("CameraServer:add_config_cams: type=Amcrest1")
        #        Amcrest1(self.parent, True,
        #                 self.parent.cam_config['user'], self.parent.cam_config['password'],
        #                 config=a_config) # manifest=data
        #    else:
        #        self.parent.logger.error("Unknown Camera type '%s'" % (a_config['type']))
        #for param in self.polyConfig['customParams']:
        #    # Look for customParam starting with hub_
        #    match = re.match( "hub_(.*)", param, re.I)
        #    if match is not None:
        #        # The hub address is everything following the hub_
        #        address = match.group(1)
        #        self.l_info('discover','got param {0} address={1}'.format(param,address))
        #        # Get the customParam value which is json code
        #        #  { "name": "HarmonyHub FamilyRoom", "host": "192.168.1.86" }
        #        cfg = self.polyConfig['customParams'][param]
        #        try:
        #            cfgd = json.loads(cfg)
        #        except:
        #            err = sys.exc_info()[0]
        #            self.l_error('discover','failed to parse cfg={0} Error: {1}'.format(cfg,err))
        #        # Check that name and host are defined.
        #        addit = True
        #        if not 'name' in cfgd:
        #            self.l_error('discover','No name in customParam {0} value={1}'.format(param,cfg))
        #            addit = False
        #        if not 'host' in cfgd:
        #            self.l_error('discover','No host in customParam {0} value={1}'.format(param,cfg))
        #            addit = False
        #        if addit:
        #            self.hubs.append({'address': address, 'name': get_valid_node_name(cfgd['name']), 'host': cfgd['host'], 'port': 5222})
        pass
        
    def discover_foscam(self):
        self.l_info("discover_foscam"," Polling for Foscam MJPEG cameras %s" % (self.foscam_mjpeg))
        cams = foscam_poll(LOGGER)
        self.l_info("discover_foscam"," Got cameras: " + str(cams))
        for cam in cams:
            cam['id'] = cam['id'].lower()
            self.l_info("discover_foscam","Checking to add camera: %s %s" % (cam['id'], cam['name']))
            lnode = self.get_node(cam['id'])
            if lnode:
                self.l_info("discover_foscam","TODO: Already exists, updating %s %s" % (cam['id'], cam['name']))
                #lnode.update_config(self.parent.cam_config['user'], self.parent.cam_config['password'], udp_data=cam)
            else:
                if cam['mtype'] == "MJPEG":
                    self.l_info("discover_foscam","Adding FoscamMJPEG camera: %s" % (cam['name']))
                    FoscamMJPEG(self.parent, True, self.parent.cam_config['user'], self.parent.cam_config['password'], udp_data=cam)
                    self.incr_num_cams()
                elif cam['mtype'] == "HD2":
                    self.l_info("discover_foscam","Adding FoscamHD camera: %s" % (cam['name']))
                    FoscamHD2(self.parent, True, self.parent.cam_config['user'], self.parent.cam_config['password'], udp_data=cam)
                    self.incr_num_cams()
                else:
                    self.l_error("discover_foscam","Unknown type %s for Foscam Camera %s" % (cam['type'],cam['name']))
            self.l_info("discover_foscam","Done")
        
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

    def set_foscam_mjpeg(self,val):
        if val is None:
            val = 0
        self.foscam_mjpeg = int(val)
        self.setDriver('GV4', self.foscam_mjpeg)
        
    def set_debug_mode(self,val):
        if val is None:
            val = 0
        self.debug_mode = int(val)
        self.setDriver('GV5', self.debug_mode)

    def set_short_poll(self,val):
        if val is None:
            val = 0
        self.short_poll = int(val)
        self.setDriver('GV6', self.short_poll)

    def set_long_poll(self,val):
        if val is None:
            val = 0
        self.long_poll = int(val)
        self.setDriver('GV7', self.long_poll)
        
    def cmd_install_profile(self,command):
        self.l_info("_cmd_install_profile","installing...")
        self.poly.installprofile()

    def cmd_set_foscam_mjpeg(self,command):
        """ Enable/Disable Foscam UDP Searching
              0 = Off
              1 = 10 second query
              2 = 20 second query
              3 = 30 second query
              4 = 60 second query
        """
        val = int(command.get('value'))
        self.l_info("cmd_set_foscam_mjpeg",val)
        self.set_foscam_mjpeg(val)
    
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
        'SET_FOSCAM_MJPEG': cmd_set_foscam_mjpeg,
        #'SET_DM': _set_debug_mode,
        #'SET_SHORTPOLL': _cmd_set_shortpoll,
        #'SET_LONGPOLL':  _cmd_set_longpoll
    }
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},
        {'driver': 'GV1', 'value': 0, 'uom': 56}, # Major version of this code.
        {'driver': 'GV2', 'value': 0, 'uom': 56}, # Minor version of this code.
        {'driver': 'GV3', 'value': 0, 'uom': 56}, # Number of cameras we manage
        {'driver': 'GV4', 'value': 0, 'uom': 25}, # Foscam Polling
        {'driver': 'GV5', 'value': 0, 'uom': 25}, # Debug (Log) Mode
        {'driver': 'GV6', 'value': 5, 'uom': 25}, # shortpoll
        {'driver': 'GV7', 'value': 60, 'uom': 25}  # longpoll
    ]

