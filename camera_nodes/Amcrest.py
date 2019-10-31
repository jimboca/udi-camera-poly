
import os
import polyinterface
from amcrest import AmcrestCamera
from functools import partial
from camera_funcs import myint,myfloat,int2str,ip2long,long2ip,isBitI,setBit,clearBit,bool2int,str2int,str_d,get_valid_node_name
from camera_nodes import Motion
import xml.etree.ElementTree as ET

LOGGER = polyinterface.LOGGER

#linkage Motion alarm linkage
#( bit3 | bit2 | bit1 | bit0 )
#bit0:Ring
#bit1:Send mail
#bit2:Snap picture
#bit3:Record
linkage_bits = { "ring":0, "send_mail":1, "snap_picture":2, "record":3 }

class Amcrest(polyinterface.Node):
    def __init__(self, controller, user, password, config=None, node_data=None):
        self.user = user
        self.password = password
        if node_data is None:
            # Only config is passed in for a new node, so we need start to get some info.
            self.init      = True
            self.update_config(user,password,config=config)
        else:
            # Re-adding an existing node, which happens on restart.
            self.init      = False
            self.name      = node_data['name']
            self.address   = node_data['address']
        self.st  = False
        super(Amcrest, self).__init__(controller, self.address, self.address, self.name)

    # This is called by __init__ and the Controller during a discover
    def update_config(self,user,password,config=None):
        self.name      = "NewCamera"
        self.host      = config['host']
        if 'port' in config:
            self.port = config['port']
        else:
            self.port = 80
        # Need to connect to camera to get it's info.
        self.l_info("init","connecting to {0}".format(self.host))
        #
        # TODO: What happens in error? try/catch?
        self.camera    = AmcrestCamera(self.host, self.port, self.user, self.password).camera
        self.l_info("init","got {0}".format(self.camera))
        # Node_Address is last 14 characters of the serial number
        self.address = get_valid_node_name(self.camera.serial_number.split()[0][-14:].lower())
        # Name is the machine name
        self.name      = get_valid_node_name(self.camera.machine_name.split('=')[-1].rstrip())
        #self.ip = get_network_ip(self.host)
        self.ip = "1.2.3.4"
        self.sys_ver      = 0

    def update_drivers(self):
        self.setDriver('GV2',  ip2long(self.ip))
        self.setDriver('GV3',  self.port)
        self.setDriver('GV11', self.sys_ver)

    def start(self):
        if self.init:
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
        # Add my motion node now that the camera is defined.
        self.motion = self.controller.addNode(Motion(self.controller, self, self))
        # Call query to pull in the params before adding the motion node.
        self.query();

    def query(self):
        """ query the camera """
        # pylint: disable=unused-argument
        self.l_info("query","start")
        self.get_status()
        if self.st:
            # Full System Version
            self.full_sys_ver = str_d(self.camera.software_information[0].split('=')[1]);
            sys_ver_l = self.full_sys_ver.split('.')
            # Just the first part as a float
            self.sys_ver      = myfloat("{0}.{1}".format(sys_ver_l[0],sys_ver_l[1]))
            self.setDriver('GV1', self.sys_ver)
            # Initialize network info
            # Motion
            self.setDriver('GV5', bool2int(self.camera.is_motion_detector_on()))
            self.get_motion_params()
            self.setDriver('GV6', self.record_enable)
            self.setDriver('GV7', self.mail_enable)
            self.setDriver('GV8', self.snapshot_enable)
            self.setDriver('GV9', self.snapshot_times)
            # All done.
            self.reportDrivers()
        self.l_info("query","done")
        return True

    def shortPoll(self):
        """ Nothing to poll?  """
        #response = os.system("ping -c 1 -w2 " + self.ip + " > /dev/null 2>&1")
        # Fix the motion params if it failed the last time.
        #if not self.set_motion_params_st and self.connected == 1:
        #    self.set_motion_params()
        #self.l_debug("poll","none")
        return

    def longPoll(self):
        self.l_info("long_poll","start")
        # get_status handles properly setting self.connected and the driver
        # so just call it.
        self.get_status()
        self.l_debug("long_poll","done")
        return

    def l_info(self, name, string):
        LOGGER.info("%s:%s:%s: %s" %  (self.id,self.name,name,string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s:%s: %s" % (self.id,self.name,name,string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s:%s: %s" % (self.id,self.name,name,string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s:%s: %s" % (self.id,self.name,name,string))

    # **********************************************************************
    #
    # Functions to set drivers
    #

    def set_st(self,value,force=False):
        if not force and self.st == value:
            return value
        self.st = value
        if value:
            self.setDriver('ST', 1)
        else:
            self.setDriver('ST', 0)
        return value

    # **********************************************************************
    #
    # Functions to grab current state of camera.
    #

    def get_status(self):
        """
        Simple check if the camera is responding.
        """
        self.l_info("get_status","%s:%s" % (self.host,self.port))
        # Get the led_mode since that is the simplest return status
        rc = self.camera.machine_name
        self.l_info("get_status","rc={0}".format(rc))
        if rc == 0:
            connected = False
            self.l_error("get_status"," Failed to get_status: {0}".format(rc))
        else:
            connected = True
        return self.set_st(connected)

    def get_motion_status(self):
        """
        Called by motion node to return the current motion status.
        0 = Off
        1 = On
        2 = Unknown
        """
        self.l_error('get_motion_status','Not implemented yet')
        #self.get_status()
        #if not self.cam_status or not 'alarm_status' in self.cam_status:
        #    return 2
        #return int(self.cam_status['alarm_status'])

    def get_motion_params(self):
        self.l_info("get_motion_params","start")
        self.mail_enable     = 0
        self.record_enable   = 0
        self.snapshot_enable = 0
        self.snapshot_times  = 0
        #
        # Grab all motion detect params in one call
        #
        ret = self.camera.motion_detection
        for s in ret.split():
            if '=' in s:
                a = s.split('=')
                name  = a[0]
                value = a[1]
                if '.MailEnable' in name:
                    self.l_info("get_motion_params","name='{0}' value={1}".format(name,value))
                    self.mail_enable = str2int(value)
                elif '.RecordEnable' in name:
                    self.l_info("get_motion_params","name='{0}' value={1}".format(name,value))
                    self.record_enable = str2int(value)
                elif '.SnapshotEnable' in name:
                    self.l_info("get_motion_params","name='{0}' value={1}".format(name,value))
                    self.snapshot_enable = str2int(value)
                elif '.SnapshotTimes' in name:
                    self.l_info("get_motion_params","name='{0}' value={1}".format(name,value))
                    self.snapshot_times = int(value)
        self.l_info("get_motion_params","done")
        return

    # **********************************************************************
    #
    # Functions to set state of camera.
    #
    def set_vmd_enable(self, driver=None, **kwargs):
        """
        Video Motion Detect
        """
        value = kwargs.get("value")
        if value is None:
            self.l_error("set_vmd_enable","_set_vmd_enable not passed a value: %s" % (value))
            return False
        # TODO: Should use the _driver specified function instead of int.
        self.l_info("set_vmd_enable","_set_vmd_enable %s" % (value))
        self.camera.motion_detection = int2str(value)
        self.l_info("set_vmd_enable","is_motion_detector_on: {0}".format(self.camera.is_motion_detector_on()))
        self.setDriver(driver, bool2int(self.camera.is_motion_detector_on()))
        return True

    def set_motion_param(self, driver=None, param=None, convert=None, **kwargs):
        value = kwargs.get("value")
        if value is None:
            self.l_error("set_motion_param","not passed a value: %s" % (value) )
            return False
        if convert is not None:
            if convert == "int2str":
                sval = int2str(value)
            elif convert == "int":
                sval = int(value)
            else:
                self.l_info("set_motion_param","unknown convert={0}".format(convert))
        command = 'configManager.cgi?action=setConfig&MotionDetect[0].EventHandler.{0}={1}'.format(param,sval)
        self.l_info("set_motion_param","comand={0}".format(command))
        rc = self.camera.command(command)
        self.l_debug("set_motion_param","rc={0}".format(rc))
        # Used to check content here, but status_code seems better.
        if hasattr(rc,'status_code'):
            if rc.status_code == 200:
                self.setDriver(driver, int(value))
                return True
            else:
                self.l_error("set_motion_param","command failed response_code={0}".format(rc.status_code))
        else:
            self.l_error("set_motion_param","command response object does not contain a status_code {0}".format(rc))
        self.l_error("set_motion_param","failed to set {0}={1} return={2}".format(param,value,rc))
        return False

    def cmd_set_vmd_enable(self,command):
        value = command.get("value")
        return self.set_vmd_enable(driver="GV5", value=value)

    def cmd_set_vmd_record(self,command):
        value = command.get("value")
        self.set_motion_param(driver="GV6", param='RecordEnable', convert="int2str", value=value)

    def cmd_set_vmd_email(self,command):
        value = command.get("value")
        self.set_motion_param(driver="GV7", param='MailEnable', convert="int2str", value=value)

    def cmd_set_vmd_snapshot(self,command):
        value = command.get("value")
        self.set_motion_param(driver="GV8", param='SnapshotEnable', convert="int2str", value=value)

    def cmd_set_vmd_snapshot_count(self,command):
        value = command.get("value")
        self.set_motion_param(driver="GV9", param='SnapshotTimes', convert="int", value=value)

    def cmd_goto_preset(self, command):
        """ Goto the specified preset. """
        value = command.get("value")
        if value is None:
            self.parent.send_error("_goto_preset not passed a value: %s" % (value) )
            return False
        rc = self.camera.go_to_preset(action='start', channel=0, preset_point_number=int(value))
        self.l_info("_goto_preset","return={0}".format(rc))
        if "ok" in str_d(rc).lower():
            return True
        self.parent.send_error("_goto_preset failed to set {0} message={1}".format(int(value),rc))
        return True

    drivers = [
        {'driver': 'ST',   'value': 0,  'uom': 2},  # Responding
        {'driver': 'GV0',  'value': 0,  'uom': 2},  # -- Not used --
        {'driver': 'GV1',  'value': 0,  'uom': 56}, # Camera System Version
        {'driver': 'GV2',  'value': 0,  'uom': 56}, # IP Address
        {'driver': 'GV3',  'value': 0,  'uom': 56}, # Port
        {'driver': 'GV4',  'value': 0,  'uom': 2},  # -- Not Used --
        {'driver': 'GV5',  'value': 0,  'uom': 2},  # Video motion detect
        {'driver': 'GV6',  'value': 0,  'uom': 2},  #
        {'driver': 'GV7',  'value': 0,  'uom': 2},  #
        {'driver': 'GV8',  'value': 0,  'uom': 2},  #
        {'driver': 'GV9',  'value': 0,  'uom': 56}  #
    ]
    commands = {
        'QUERY': query,
        'SET_VMD_ENABLE':         cmd_set_vmd_enable,
        'SET_VMD_RECORD':         cmd_set_vmd_record,
        'SET_VMD_EMAIL':          cmd_set_vmd_email,
        'SET_VMD_SNAPSHOT':       cmd_set_vmd_snapshot,
        'SET_VMD_SNAPSHOT_COUNT': cmd_set_vmd_snapshot_count,
        'SET_POS':                cmd_goto_preset,
        #'REBOOT':    _reboot,
    }
    # The nodeDef id of this camers.
    id = 'Amcrest'
