
import os
import polyinterface
from functools import partial
from camera_funcs import myint,myfloat,ip2long,long2ip,isBitI,setBit,clearBit
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
            self.host      = config['host']
            if 'port' in config:
                self.port = config['port']
            else:
                self.port = 80
            self.l_info("init","connecting to {0}".format(self.host))
            self.camera    = AmcrestCamera(self.host, self.port, self.user, self.password).camera
            self.l_info("init","got {0}".format(self.camera))
            # Node_Address is last 14 characters of the serial number
            self.address = self.camera.serial_number.decode('utf-8').split()[0][-14:].lower()
            # Name is the machine name
            self.name      = self.camera.machine_name.decode('utf-8').split('=')[-1].rstrip()
        else:
            # Re-adding an existing node, which happens on restart.
            self.init      = False
            self.name      = node_data['name']
            self.address   = node_data['address']
        self.st  = False
        super(Amcrest, self).__init__(controller, self.address, self.address, self.name)

    # This is called by __init__ and the Controller during a discover
    def update_config(self,user,password,udp_data=None):
        self.name      = udp_data['name']
        self.ip        = udp_data['ip']
        self.port      = udp_data['port']
        self.full_sys_ver = str(udp_data['sys'])
        self.sys_ver   = self.parse_sys_ver(self.full_sys_ver)

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
        # Call query to pull in the params before adding the motion node.
        self.query();

        
    drivers = [
        {'driver': 'ST',   'value': 0,  'uom': 2},  # Responding
        {'driver': 'GV0',  'value': 0,  'uom': 2},  # Motion Ring
        {'driver': 'GV1',  'value': 0,  'uom': 56}, # Major version of this code.
        {'driver': 'GV2',  'value': 0,  'uom': 56}, # IP Address
        {'driver': 'GV3',  'value': 0,  'uom': 56}, # Port
        {'driver': 'GV4',  'value': 1,  'uom': 2},  # Motion Record
        {'driver': 'GV5',  'value': 0,  'uom': 25}, # IR LED Mode
        {'driver': 'GV6',  'value': 5,  'uom': 2},  # Alarm Motion Armed
        {'driver': 'GV7',  'value': 0,  'uom': 2},  # Alarm Send Mail
        {'driver': 'GV8',  'value': 0,  'uom': 25}, # Motion Sensitivity
        {'driver': 'GV9',  'value': 0,  'uom': 2},  # Motion Compensation (Not used?)
        {'driver': 'GV10', 'value': 0,  'uom': 25}, # Motion Trigger Interval
        {'driver': 'GV11', 'value': 0,  'uom': 56}, # Camera System Version
        {'driver': 'GV12', 'value': 0,  'uom': 56}, # Minor version of this code.
        {'driver': 'GV13', 'value': 0,  'uom': 25}, # Snap Interval
        {'driver': 'GV14', 'value': 0,  'uom': 2}   # Motion Picture
    ]
    id = 'FoscamHD2'
    commands = {
        'QUERY': query,
        'SET_IRLED':      cmd_set_irled,      # GV5
        'SET_ALMOA':      cmd_set_almoa,      # GV6
        'SET_MO_MAIL':    cmd_set_mo_mail,    # GV7
        'SET_ALMOS':      cmd_set_almos,      # GV8
        'SET_MO_TRIG':    cmd_set_mo_trig,    # GV10
        'SET_MO_RING':    cmd_set_mo_ring,    # GV0
        'SET_MO_PIC':     cmd_set_mo_pic,     # GV14
        'SET_MO_REC':     cmd_set_mo_rec,     # GV4
        'SET_MO_PIC_INT': cmd_set_mo_pic_int, # GV13
        'SET_POS':        cmd_goto_preset,
        'REBOOT':         cmd_reboot,
    }
    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
