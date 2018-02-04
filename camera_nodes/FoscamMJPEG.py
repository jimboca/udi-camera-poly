
import os
import polyinterface
#from Motion import Motion
from functools import partial
from camera_funcs import myint,myfloat,ip2long,long2ip

LOGGER = polyinterface.LOGGER

class FoscamMJPEG(polyinterface.Node):
    """
    This is the class that all the Nodes will be represented by. You will add this to
    Polyglot/ISY with the controller.addNode method.

    Class Variables:
    self.primary: String address of the Controller node.
    self.parent: Easy access to the Controller Class from the node itself.
    self.address: String address of this Node 14 character limit. (ISY limitation)
    self.added: Boolean Confirmed added to ISY

    Class Methods:
    start(): This method is called once polyglot confirms the node is added to ISY.
    setDriver('ST', 1, report = True, force = False):
        This sets the driver 'ST' to 1. If report is False we do not report it to
        Polyglot/ISY. If force is True, we send a report even if the value hasn't changed.
    reportDrivers(): Forces a full update of all drivers to Polyglot/ISY.
    query(): Called when ISY sends a query request to Polyglot for this specific node
    """
    def __init__(self, controller, user, password, udp_data=None, node_data=None):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param controller: Reference to the Controller class
        :param primary: Controller address
        :param address: This nodes address
        :param name: This nodes name
        """
        self.user = user
        self.password = password
        if udp_data is not None:
            self.init      = True
            self.address   = udp_data['id'].lower()
            self.update_config(user,password,udp_data=udp_data)
        elif node_data is not None:
            self.init      = False
            self.name      = node_data['name']
            self.address   = node_data['address']
        else:
            self.l_error("__init__","one of node_data or udp_data must be passed in")
            return False
        self.st = False
        super(FoscamMJPEG, self).__init__(controller, self.address, self.address, self.name)

    # This is called by __init__ and the Controller during a discover
    def update_config(self,user,password,udp_data=None):
        self.name      = udp_data['name']
        self.auth_mode = self.get_auth_mode(udp_data['sys'])
        self.ip        = udp_data['ip']
        self.port      = udp_data['port']
        self.full_sys_ver = str(udp_data['sys'])
        self.sys_ver   = self.parse_sys_ver(self.full_sys_ver)

    def update_drivers(self):
        self.setDriver('ST', 1)
        self.setDriver('GV2',  ip2long(self.ip))
        self.setDriver('GV3',  self.port)
        self.setDriver('GV10', self.auth_mode)
        self.setDriver('GV11', self.sys_ver)

    def start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot. Only happens once.
        """
        if self.init:
            # __init__ sets init to True when upd_data is passed in, update_drivers needs to be called.
            self.update_drivers()
        else:
            # It's an existing Node, so get the info we need from it.
            g_ip    = self.getDriver('GV2')
            g_port  = self.getDriver('GV3')
            g_authm = self.getDriver('GV10')
            self.l_info("start","ip={0} port={1} auth_mode={2}".format(g_ip,g_port,g_authm))
            if int(g_ip) == 0:
                self.l_error("start","The IP address (GV2) was set to zero?  That's not good, you will need to run discover again")
            if int(g_port) == 0:
                self.l_error("start","The port (GV3) was set to zero?  That's not good, you will need to run discover again")
            self.ip        = long2ip(int(g_ip))
            self.port      = g_port
            self.auth_mode = int(g_authm)            
            self.l_info("start","ip={0} port={1} auth_mode={2}".format(self.ip,self.port,self.auth_mode))
            # This will force query to get it
            self.sys_ver      = 0
            self.full_sys_ver = None
            # Make sure drivers are up to date.
            self.update_drivers()
        # Init these in case we can't query.
        self.cam_status = {}
        self.params = {}
        for param in ('led_mode', 'alarm_motion_armed', 'alarm_mail', 'alarm_motion_sensitivity', 'alarm_motion_compensation', 'alarm_upload_interval'):
            if not param in self.params:
                self.params[param] = 0
        # Call query to pull in the params before adding the motion node.
        self.query();
        # Add my motion node now that the camera is defined.
        # TODO: self.motion = Motion(parent, self, manifest)
        # Tell the camera to ping the parent server on motion.
        #self.set_alarm_params({
        #    'motion_armed': 1,
        #    'http':         1,
        #    'http_url':     "http://%s:%s/motion/%s" % (parent.server.server_address[0], parent.server.server_address[1], self.motion.address)
        #});
        # Query again now that we have set paramaters
        #self.query();

    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.l_info("query","...")
        # Get current camera params.
        self.get_params();
        # Get current camera status.
        self.get_status();
        if self.params:
            self.setDriver('GV5', self.params['led_mode'])
            self.setDriver('GV6', self.params['alarm_motion_armed'])
            self.setDriver('GV7', self.params['alarm_mail'])
            self.setDriver('GV8', self.params['alarm_motion_sensitivity'])
            self.setDriver('GV9', self.params['alarm_motion_compensation'])
            self.setDriver('GV13', self.params['alarm_upload_interval'])
        self.reportDrivers()
        self.l_info("query","done")
        return True

    def shortPoll(self):
        """ Nothing to poll?  """
        #response = os.system("ping -c 1 -w2 " + self.ip + " > /dev/null 2>&1")
        return

    def longPoll(self):
        self.l_info("long_poll","...")
        # get_status handles properly setting self.st and the driver
        # so just call it.
        self.get_status()
    
    def set_st(self,value,force=False):
        if not force and self.st == value:
            return True
        self.st = value
        if value:
            self.setDriver('ST', 1)
        else:
            self.setDriver('ST', 0)

    def parse_sys_ver(self,sys_ver):
        """ 
        Given the camera system version as a string, parse into what we 
        show, which is the last 2 digits
        """
        vnums = sys_ver.split(".")
        if len(vnums) == 4:
            self.l_debug("parse_sys_ver","{0} 0={1} 1={2} 2={3} 3={4}".format(sys_ver,vnums[0],vnums[1],vnums[2],vnums[3]))
            ver = myfloat("%d.%d" % (int(vnums[2]),int(vnums[3])),2)
            self.l_debug("parse_sys_ver","ver={}".format(ver))
            return ver
        else:
            self.l_waning("parse_sys_ver","Unknown sys_Ver{}".format(sys_ver))
            return None
        
    def get_auth_mode(self,sys_ver):
        """ 
        Given the camera system version as a string, figure out the 
        authorization mode.  Default is 0 (Basic) but if last 2 
        digits of sys_ver are > 2.52 then use 1 (Digest)
        """
        auth_mode = 0
        vnums = sys_ver.split(".")
        if int(vnums[2]) >= 2 and int(vnums[3]) > 52:
            auth_mode = 1
        self.l_debug("get_auth_mode"," ".format(auth_mode))
        return auth_mode

    def http_get(self, path, payload = {}):
        """ Call http_get on this camera for the specified path and payload """
        return self.parent.http_get(self.ip,self.port,self.user,self.password,path,payload,auth_mode=self.auth_mode)
        
    def http_get_and_parse(self, path, payload = {}):
        """ 
        Call http_get and parse the returned Foscam data into a hash.  The data 
        all looks like:  var id='000C5DDC9D6C';
        """
        data = self.http_get(path,payload)
        if data is False:
            return False
        ret  = {}
        for item in data.splitlines():
            param = item.replace('var ','').replace("'",'').strip(';').split('=')
            ret[param[0]] = param[1]
        return ret
    
    def get_params(self):
        """ Call get_params and get_misc on the camera and store in params """
        params = self.http_get_and_parse("get_params.cgi")
        if not params:
            self.l_error("get_params","Failed")
            self.set_st(False)
            return False
        self.set_st(True)
        self.params = self.http_get_and_parse("get_params.cgi")
        misc = self.http_get_and_parse("get_misc.cgi")
        self.params['led_mode'] = misc['led_mode']

    def set_alarm_params(self,params):
        """ 
        Set the sepecified alarm params on the camera
        """
        self.l_info("set_alarm_params","%s" % (params))
        return self.http_get("set_alarm.cgi",params)

    def set_misc_params(self,params):
        """ 
        Set the sepecified misc params on the camera
        """
        self.l_info("set_misc_params"," %s" % (params))
        return self.http_get("set_misc.cgi",params)

    def decoder_control(self,params):
        """ 
        Pass in decoder command
        """
        self.l_info("set_decoder_control","%s" % (params))
        return self.http_get("decoder_control.cgi",params)

    def get_motion_status(self):
        """
        Called by motion node to return the current motion status.
        0 = Off
        1 = On
        2 = Unknown
        """
        self.get_status()
        if not self.cam_status or not 'alarm_status' in self.cam_status:
            return 2
        return int(self.cam_status['alarm_status'])

    def set_motion_status(self,value):
        """
        Called by motion node to set the current motion status.
        """
        self.cam_status['alarm_status'] = value

    def get_status(self,report=True):
        """ 
        Call get_status on the camera and store in status
        """
        # Can't spit out the device name cause we might not know it yet.
        self.l_info("get_status","%s:%s" % (self.ip,self.port))
        # Get the status
        status = self.http_get_and_parse("get_status.cgi")
        if status:
            connected = True
            self.cam_status = status
            # Update sys_ver if it's different
            if self.full_sys_ver != str(self.cam_status['sys_ver']):
                self.l_debug("get_status",self.cam_status)
                self.l_info("get_status","New sys_ver %s != %s" % (self.full_sys_ver,str(self.cam_status['sys_ver'])))
                self.full_sys_ver = str(self.cam_status['sys_ver'])
                new_ver = self.parse_sys_ver(self.cam_status['sys_ver'])
                if new_ver is not None:
                    self.sys_ver = new_ver
                    self.setDriver('GV11', self.sys_ver)
        else:
            self.l_error("get_params","Failed to get_status")
            # inform the motion node there is an issue if we have a motion node
            if hasattr(self,'motion'):
                self.motion.motion(2)
            else:
                self.cam_status['alarm_status'] = 2
            connected = False
        self.set_st(connected)

    def set_alarm_param(self, driver=None, param=None, command=None):
        value = command.get("value")
        if value is None:
            self.l_error("set_alarm_param not passed a value: %s" % (value) )
            return False
        # TODO: Should use the _driver specified function instead of int.
        if not self.set_alarm_params({ param: int(value)}):
            self.l_error("set_alarm_param","failed to set %s=%s" % (param,value) )
        # TODO: Dont' think I should be setting the driver?
        self.setDriver(driver, myint(value))
        # The set_alarm param is without the '_alarm' prefix
        self.params['alarm_'+param] = myint(value)
        return True

    def set_misc_param(self, driver=None, param=None, value=None):
        if value is None:
            self.l_error("set_misc_param"," not passed a value for driver %s: %s" % (driver, value) )
            return False
        # TODO: Should use the _driver specified function instead of int.
        if not self.set_misc_params({ param: int(value)}):
            self.l_error("set_misc_param"," failed to set %s=%s" % (param,value) )
        # TODO: Dont' think I should be setting the driver?
        self.setDriver(driver, myint(value))
        # The set_misc param
        self.params[param] = myint(value)
        return True

    def cmd_reboot(self, command):
        """ Reboot the Camera """
        return self.http_get("reboot.cgi",{})

    def cmd_set_irled(self, command):
        """ Set the irled off=94 on=95 """
        value = int(command.get("value"))
        if value is None:
            self.l_error("cmd_set_irled"," not passed a value: %s" % (value) )
            return False
        if value == 0:
            dvalue = 94
        else:
            dvalue = 95
        if self.decoder_control( { 'command': dvalue} ):
            # TODO: Not storing this cause the camera doesn't allow us to query it.
            #self.setDriver("GVxx", myint(value))
            return True
        self.l_error("cmd_set_irled","failed to set %s" % (dvalue) )
        return False

    def cmd_set_authm(self, command):
        """ Set the auth mode 0=Basic 1=Digest """
        value = int(command.get("value"))
        if value is None:
            self.l_error("cmd_set_authm"," not passed a value: %s" % (value) )
            return False
        self.auth_mode = int(value)
        self.l_debug("set_authm",self.auth_mode)
        self.setDriver("GV10", self.auth_mode)
        # Since they changed auth mode, make sure it works.
        self.query()
        self.motion.query()
        return True

    def cmd_goto_preset(self, command):
        """ Goto the specified preset. 
              Preset 1 = Command 31
              Preset 2 = Command 33
              Preset 3 = Command 35
              Preset 16 = Command 61
              Preset 32 = Command 93
            So command is ((value * 2) + 29)
        """
        value = int(command.get("value"))
        if value is None:
            self.l_error("cmd_goto_preset"," not passed a value: %s" % (value) )
            return False
        value * 2 + 29
        value = myint((value * 2) + 29)
        if not self.decoder_control( { 'command': value} ):
            self.l_error("cmd_goto_preset"," failed to set %s" % (value) )
        return True

    def l_info(self, name, string):
        LOGGER.info("%s:%s:%s: %s" %  (self.id,self.name,name,string))
        
    def l_error(self, name, string):
        LOGGER.error("%s:%s:%s: %s" % (self.id,self.name,name,string))
        
    def l_warning(self, name, string):
        LOGGER.warning("%s:%s:%s: %s" % (self.id,self.name,name,string))
        
    def l_debug(self, name, string):
        LOGGER.debug("%s:%s:%s: %s" % (self.id,self.name,name,string))

    def cmd_set_ledm(self,command):
        self.set_misc_param(driver="GV5", param='led_mode', value=command.get("value"))

    def cmd_set_almoa(self,command):
        self.set_misc_param(driver="GV6", param='motion_armed', value=command.get("value"))

    def cmd_set_alml(self,command):
        self.set_misc_param(driver="GV7", param='motion_mail', value=command.get("value"))

    def cmd_set_almos(self,command):
        self.set_misc_param(driver="GV8", param='motion_sensitivity', value=command.get("value"))

    def cmd_set_almoc(self,command):
        self.set_misc_param(driver="GV9", param='motion_compensation', value=command.get("value"))

    def cmd_set_upint(self,command):
        self.set_misc_param(driver="GV13", param='upload_interval', value=command.get("value"))

    drivers = [
        {'driver': 'ST',   'value': 0,  'uom': 2},
        {'driver': 'GV1',  'value': 0,  'uom': 56}, # Major version of this code.
        {'driver': 'GV2',  'value': 0,  'uom': 56}, # IP Address
        {'driver': 'GV3',  'value': 0,  'uom': 56}, # Port
        {'driver': 'GV4',  'value': 0,  'uom': 2},  # No longer used.
        {'driver': 'GV5',  'value': 0,  'uom': 25}, # Network LED Mode
        {'driver': 'GV6',  'value': 0,  'uom': 2},  # Alarm Motion Armed
        {'driver': 'GV7',  'value': 0,  'uom': 2},  # Alarm Send Mail
        {'driver': 'GV8',  'value': 0,  'uom': 25}, # Motion Sensitivity
        {'driver': 'GV9',  'value': 0,  'uom': 2},  # Motion Compensation
        {'driver': 'GV10', 'value': 0,  'uom': 25}, # Authorization Mode
        {'driver': 'GV11', 'value': 0,  'uom': 56}, # Camera System Version
        {'driver': 'GV12', 'value': 0,  'uom': 56}, # Minor version of this code.
        {'driver': 'GV13', 'value': 0,  'uom': 25}  # Upload Interval
    ]
    id = 'FoscamMJPEG'
    """
    id of the node from the nodedefs.xml that is in the profile.zip. This tells
    the ISY what fields and commands this node has.
    """
    commands = {
        'QUERY': query,
        'SET_IRLED': cmd_set_irled,
        'SET_LEDM':  cmd_set_ledm,
        'SET_ALMOA': cmd_set_almoa,
        'SET_ALML':  cmd_set_alml,
        'SET_ALMOS': cmd_set_almos,
        'SET_ALMOC': cmd_set_almoc,
        'SET_UPINT': cmd_set_upint,
        'SET_AUTHM': cmd_set_authm,
        'SET_POS':   cmd_goto_preset,
        'REBOOT':    cmd_reboot,
    }
    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
