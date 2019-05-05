
import os
import polyinterface
from functools import partial
from camera_funcs import myint,myfloat,ip2long,long2ip,isBitI,setBit,clearBit
from camera_nodes import Motion
import xml.etree.ElementTree as ET

LOGGER = polyinterface.LOGGER

#linkage Motion alarm linkage
#( bit3 | bit2 | bit1 | bit0 )
#bit0:Ring
#bit1:Send mail
#bit2:Snap picture
#bit3:Record
#bit7:Push To Phone
#2018-12-07 18:59:08,821 [Controller] [DEBUG] FoscamHD2:CamFamilyRoom:get_cam_motion_detect_config: linkage=0 ring=0 send_mail=0 snap_picture=0 record=0 push=0
#2018-12-07 18:59:36,483 [Controller] [DEBUG] FoscamHD2:CamFamilyRoom:get_cam_motion_detect_config: linkage=1 ring=1 send_mail=0 snap_picture=0 record=0 push=0
#2018-12-07 18:59:58,469 [Controller] [DEBUG] FoscamHD2:CamFamilyRoom:get_cam_motion_detect_config: linkage=2 ring=0 send_mail=1 snap_picture=0 record=0 push=0
#2018-12-07 19:00:20,040 [Controller] [DEBUG] FoscamHD2:CamFamilyRoom:get_cam_motion_detect_config: linkage=4 ring=0 send_mail=0 snap_picture=1 record=0 push=0
#2018-12-07 19:00:44,441 [Controller] [DEBUG] FoscamHD2:CamFamilyRoom:get_cam_motion_detect_config: linkage=8 ring=0 send_mail=0 snap_picture=0 record=1 push=0
#2018-12-07 19:01:19,768 [Controller] [DEBUG] FoscamHD2:CamFamilyRoom:get_cam_motion_detect_config: linkage=128 ring=0 send_mail=0 snap_picture=0 record=0 push-1
# No idea what 16, 32, 64 are?
#                    1           2                4              8       16      32       64      128
linkage_bits = { "ring":0, "send_mail":1, "snap_picture":2, "record":3, "16":4, "32":5, "64":6, "push":7 }

IS_AMBA = {
    "FI9826P+V2" : False,
    "FI9828P+V2" : False,
    "R2+V4"      : True,
    "R4"         : True,
    "FI9900P"    : True,
    "FI9928P"    : True,
}

class FoscamHD2(polyinterface.Node):
    def __init__(self, controller, user, password, udp_data=None, node_data=None):
        self.user = user
        self.password = password
        # Use Digest authorization for all HD cameras?
        self.auth_mode = 0
        if udp_data is not None:
            # This is when camera is discovered
            self.init      = True
            self.address   = udp_data['id'].lower()
            self.update_config(user,password,udp_data=udp_data)
        elif node_data is not None:
            # This is on restart when adding nodes back
            self.init      = False
            self.name      = node_data['name']
            self.address   = node_data['address']
        else:
            self.l_error("__init__","one of node_data or udp_data must be passed in")
            return False
        self.amba = False
        self.cam_status = {}
        self.st  = False
        self.set_motion_params_st = True
        super(FoscamHD2, self).__init__(controller, self.address, self.address, self.name)

    # This is called by __init__ and the Controller during a discover
    def update_config(self,user,password,udp_data=None):
        self.name      = udp_data['name']
        self.ip        = udp_data['ip']
        self.port      = udp_data['port']
        self.parse_sys_ver(udp_data['sys'])

    def update_drivers(self):
        self.setDriver('GV2',  ip2long(self.ip))
        self.setDriver('GV3',  self.port)
        self.setDriver('GV11', self.sys_s_ver)

    def start(self):
        if self.init:
            self.update_drivers()
        else:
            # It's an existing Node, so get the info we need from it.
            g_ip    = self.getDriver('GV2')
            g_port  = self.getDriver('GV3')
            self.l_info("start","ip={0} port={1} auth_mode={2}".format(g_ip,g_port,self.auth_mode))
            if int(g_ip) == 0:
                self.l_error("start","The IP address (GV2) was set to zero?  That's not good, you will need to run discover again")
            if int(g_port) == 0:
                self.l_error("start","The port (GV3) was set to zero?  That's not good, you will need to run discover again")
            self.ip        = long2ip(int(g_ip))
            self.port      = g_port
            self.l_info("start","ip={0} port={1} auth_mode={2}".format(self.ip,self.port,self.auth_mode))
            # This will force query to get it
            self.sys_s_ver    = 0
            self.sys_e_ver    = 0
            self.full_sys_ver = None
            # Make sure drivers are up to date.
            self.update_drivers()
        # Add my motion node now that the camera is defined.
        self.motion = self.controller.addNode(Motion(self.controller, self, self))
        # Call query to pull in the params before adding the motion node.
        self.query();

    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.l_info("query","start")
        # Get current camera params.
        self.get_cam_all()
        self.reportDrivers()
        self.l_info("query","done")
        return True

    def shortPoll(self):
        """ Nothing to poll?  """
        #response = os.system("ping -c 1 -w2 " + self.ip + " > /dev/null 2>&1")
        # Fix the motion params if it failed the last time.
        if not self.set_motion_params_st and self.st:
            self.set_motion_params()
        return True

    def longPoll(self):
        self.l_info("long_poll","..")
        # get_status handles properly setting self.st and the driver
        # so just call it.
        self.get_status()

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
        self.full_sys_ver = str(sys_ver)
        vnums = self.full_sys_ver.split(".")
        if len(vnums) == 4:
            self.l_debug("parse_sys_ver","{0} 0={1} 1={2} 2={3} 3={4}".format(sys_ver,vnums[0],vnums[1],vnums[2],vnums[3]))
            self.sys_s_ver = myfloat("%d.%d" % (int(vnums[0]),int(vnums[1])),2)
            self.sys_e_ver = myfloat("%d.%d" % (int(vnums[2]),int(vnums[3])),2)
            self.l_debug("parse_sys_ver","sys_s_ver={} sys_e_ver".format(self.sys_s_ver,self.sys_e_ver))
        else:
            self.l_waning("parse_sys_ver","Unknown sys_Ver{}".format(sys_ver))
            self.sys_s_ver = None
            self.sys_e_ver = None


    def get_motion_status(self):
        """
        Called by motion node to return the current motion status.
        0 = Off
        1 = On
        2 = Unknown
        """
        return 0
        self.get_status()
        if not self.cam_status or not 'alarm_status' in self.cam_status:
            return 2
        return int(self.cam_status['alarm_status'])

    def set_motion_status(self,value):
        """
        Called by motion node to set the current motion status.
        """
        self.cam_status['alarm_status'] = value

    # **********************************************************************
    #
    # Camera Access Routines
    #
    def http_get(self, cmd, payload = {}):
        """ Call http_get on this camera for the specified path and payload """
        # Doesn't accept a payload, so convert to arg
        # and neither basic or digest authmode works!?!? Must pass with command
        #path = "cgi-bin/CGIProxy.fcgi?cmd=%s&usr=%s&pwd=%s" % (cmd,self.user,self.password)
        #for key in payload:
        #    path += "&%s=%s" % (key,payload[key])
        path = "cgi-bin/CGIProxy.fcgi"
        payload['cmd'] = cmd
        payload['usr'] = self.user
        payload['pwd'] = self.password
        return self.parent.http_get(self.ip,self.port,self.user,self.password,path,payload,auth_mode=self.auth_mode)

    def http_get_and_parse(self, cmd, payload = {}):
        """
        Call http_get and parse the returned Foscam data into a hash.  The data
        all looks like:  var id='000C5DDC9D6C';
        """
        ret  = {}
        data = self.http_get(cmd,payload)
        self.l_debug("http_get_and_parse","data=%s" % (data))
        if data is False:
            code = -1
        else:
            # Return code is good, unless CGI result changes it later
            code = 0
            root = ET.fromstring(data)
            for child in root.iter():
                if child.tag == 'result':
                    code = int(child.text)
                elif child.tag != 'CGI_Result':
                    ret[child.tag] = child.text
        self.l_debug("http_get_and_parse","code=%d, ret=%s" % (code,ret))
        return code,ret

    def save_keys(self, pfx, rc, params):
        """
        Stores the parsed data in the status dict.
        """
        self.l_debug("save_keys","pfx=%s rc=%d params=%s" % (pfx,rc,params))
        if pfx not in self.cam_status:
            self.cam_status[pfx] = dict()
        if rc == 0:
            for key in sorted(params.keys()):
                self.l_debug("save_keys","%s:%s=%s" % (pfx,key,params[key]))
                self.cam_status[pfx][key] = params[key]

    def http_get_and_parse_keys(self, cmd, pfx = ""):
        """
        Calls http get, parses the keys and stores them in status dict
        """
        rc, data = self.http_get_and_parse(cmd)
        self.save_keys(pfx,rc,data)
        return rc

    # **********************************************************************

    def get_irled_state(self,report=True):
        """
        Set the status irled_status based on combination of
        irled->mode and infraLedState
          0 = Auto
          1 = Off
          2 = On
          3 = Unknown
        """
        if 'irled_state' in self.cam_status:
            cstate = self.cam_status['irled_state']
        else:
            cstate = -1
        if 'irled' in self.cam_status and 'mode' in self.cam_status['irled']:
            self.l_info("get_irled_state","irled_mode=%d" % (int(self.cam_status['irled']['mode'])))
            if int(self.cam_status['irled']['mode']) == 0:
                self.cam_status['irled_state'] = 0
            elif 'devstate' in self.cam_status and 'infraLedState' in self.cam_status['devstate']:
                self.l_info("get_irled_state","infraLedState=%d" % (int(self.cam_status['devstate']['infraLedState'])))
                if int(self.cam_status['devstate']['infraLedState']) == 0:
                    self.cam_status['irled_state'] = 1
                else:
                    self.cam_status['irled_state'] = 2
            else:
                self.cam_status['irled_state'] = 3
        else:
            self.cam_status['irled_state'] = 3
        if cstate != self.cam_status['irled_state']:
            self.setDriver('GV5', self.cam_status['irled_state'])
        self.l_info("get_irled_state","irled_state=%d" % (self.cam_status['irled_state']))

    # **********************************************************************
    #
    # Functions to grab current state of camera.
    #
    def get_product_info(self,report=True):
        rc = self.http_get_and_parse_keys('getProductAllInfo',"product")
        return rc

    def get_cam_irled(self,report=True):
        rc = self.http_get_and_parse_keys('getInfraLedConfig',"irled")
        self.get_irled_state(report)
        return rc

    def get_cam_dev_state(self,report=True):
        rc = self.http_get_and_parse_keys('getDevState',"devstate")
        self.get_irled_state(report)
        return rc

    def get_cam_dev_info(self,report=True):
        rc = self.http_get_and_parse_keys('getDevInfo',"devinfo")
        # Update sys_ver if it's different
        self.l_info('get_cam_dev_state','got {0}'.format(rc))
        if rc != -2 and rc != -1 and self.full_sys_ver != str(self.cam_status['devinfo']['hardwareVer']):
            self.l_info("get_cam_dev_info","New sys_ver %s != %s" % (self.full_sys_ver,str(self.cam_status['devinfo']['hardwareVer'])))
            self.parse_sys_ver(self.cam_status['devinfo']['hardwareVer'])
            self.setDriver('GV11', self.sys_s_ver)
        return rc

    def get_cam_motion_detect_config(self,report=True):
        mk = 'motion_detect'
        command = 'getMotionDetectConfig1' if self.amba else 'getMotionDetectConfig'
        st = self.http_get_and_parse_keys(command,mk)
        self.l_info("get_cam_motion_detect_config","st=%d" % (st))
        if st == 0:
            self.setDriver('GV6',  int(self.cam_status[mk]['isEnable']))
            if 'sensitivity' in self.cam_status[mk]:
                self.setDriver('GV8',  int(self.cam_status[mk]['sensitivity']))
            elif 'sensitivity1' in self.cam_status[mk]:
                self.setDriver('GV8',  int(self.cam_status[mk]['sensitivity1']))
            else:
                self.l_error('get_cam_motion_detect_config','No sensitivity or sensitivity1 in {}'.format(self.cam_status[mk]))
            self.setDriver('GV10', int(self.cam_status[mk]['triggerInterval']))
            self.setDriver('GV13', int(self.cam_status[mk]['snapInterval']))
            if 'linkage' in self.cam_status[mk]:
                sl = int(self.cam_status[mk]['linkage'])
                self.setDriver('GV7',  isBitI(sl,linkage_bits['send_mail']))
                self.setDriver('GV14', isBitI(sl,linkage_bits['snap_picture']))
                self.setDriver('GV4',  isBitI(sl,linkage_bits['record']))
                self.setDriver('GV0', isBitI(sl,linkage_bits['ring']))
                self.setDriver('GV15', isBitI(sl,linkage_bits['push']))
                self.l_debug('get_cam_motion_detect_config','linkage={} ring={} send_mail={} snap_picture={} record={} push={}'.
                    format(sl,
                        isBitI(sl,linkage_bits['ring']),
                        isBitI(sl,linkage_bits['send_mail']),
                        isBitI(sl,linkage_bits['snap_picture']),
                        isBitI(sl,linkage_bits['record']),
                        isBitI(sl,linkage_bits['push']),
                        ))
            else:
                self.l_error('get_cam_motion_detect_config','No linkage in {}'.format(self.cam_status[mk]))
        return st

    def get_status(self):
        self.l_info("get_status","%s:%s" % (self.ip,self.port))
        # Get the led_mode since that is the simplest return status
        rc = self.get_cam_dev_info(report=True)
        self.l_info("get_status","rc=%d" % (rc))
        if rc == 0:
            connected = True
        else:
            self.l_error("get_status"," Failed to get_status: %d" % (rc))
            # inform the motion node there is an issue if we have a motion node
            #if hasattr(self,'motion'):
            #    self.motion.motion(2)
            #else:
                # TODO: Why was this done?
                #self.cam_status['alarm_status'] = 2
            connected = False
        self.set_st(connected)

    def set_cam_all(self):
        """
        Figure out if it's an "Amba S2L" camera which uses some different http calls
        """
        if self.cam_status['product']['modelName'] in IS_AMBA:
            self.amba = IS_AMBA[self.cam_status['product']['modelName']]
            self.l_info('set_cam_all','Using known Amba setting for {}={}'
                        .format(self.cam_status['product']['modelName'],self.amba))
        else:
            # We will assume it is not...
            self.amba = False
            self.l_info('set_cam_all','Assuming NOT Amba setting for {}={}'
                        .format(self.cam_status['product']['modelName'],self.amba))
        self.l_info('set_cam_all',
                    "model={}, model_name={}, hardware_ver={}, firmware_ver={}, amba={}"
                    .format(
                        self.cam_status['product']['model'],
                        self.cam_status['product']['modelName'],
                        self.cam_status['devinfo']['hardwareVer'],
                        self.cam_status['devinfo']['firmwareVer'],
                        self.amba
                    )
                )

    def get_cam_all(self,report=True):
        """
        Call get_status on the camera and store in status
        """
        self.get_status()
        if self.st:
            self.get_product_info(report=False)
            self.get_cam_dev_state(report=False)
            self.get_cam_dev_info(report=False)
            self.set_cam_all()
            self.get_cam_motion_detect_config(report=False)

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
    # Functions to set state of camera.
    #
    def cmd_set_irled(self, command):
        """
        irled_state is an interal value based on led auto, manual, on, off settings
        See _get_irled_state for full info.
        """
        value = command.get("value")
        if value is None:
            self.l_error("cmd_set_irled","not passed a value: %s" % (value) )
            return False
        # TODO: Should use the _driver specified function instead of int.
        if int(value) == 0:
            # AUTO
            if not self.http_get("setInfraLedConfig",{"mode": int(value)}):
                self.l_error("cmd_set_irled","failed")
        elif int(value) == 1:
            # Manual
            if not self.http_get("setInfraLedConfig",{"mode": 1}):
                self.l_error("cmd_set_irled","failed")
            # Off
            if not self.http_get("closeInfraLed",{}):
                self.l_error("cmd_set_irled","failed")
        else:
            # Manual
            if not self.http_get("setInfraLedConfig",{"mode": 1}):
                self.l_error("cmd_set_irled","failed")
            # On
            if not self.http_get("openInfraLed",{}):
                self.l_error("cmd_set_irled","failed")
        # TODO: Dont' think I should be setting the driver?
        self.setDriver("GV5", myint(value))
        # The set_alarm param is without the '_alarm' prefix
        self.cam_status['irled_state'] = myint(value)
        return True

    def is_responding(self):
        if self.st:
            return True
        else:
            self.l_error("is_conncted","Camera {0}:{1} is not respoding {2}".format(self.ip,self.port,self.st))
            return False

    def set_motion_params(self):
        """
        Set all alarm motion params on the camera.  All need to be passed each time
        because if one is not passed it reverts to the default... dumb foscam api ...
        """
        if not self.is_responding():
            return False
        #self.l_debug("set_motion_params","cam_status={}".format(self.cam_status))
        self.l_info("set_motion_params","...")
        command = 'setMotionDetectConfig1' if self.amba else 'setMotionDetectConfig'
        for i in range(0, 7):
            self.cam_status['motion_detect']['schedule'+str(i)] = 281474976710655
        self.set_motion_params_st = self.http_get(command,self.cam_status['motion_detect'])
        return self.set_motion_params_st

    def set_motion_param(self, driver=None, param=None, value=None):
        self.l_debug("set_motion_param","driver={0} param={1} value={2}".format(driver,param,value))
        if not self.is_responding():
            return False
        if value is None:
            self.l_error("set_motion_param","not passed a value: %s" % (value) )
            return False
        self.get_cam_motion_detect_config(report=False)
        self.cam_status['motion_detect'][param] = myint(value)
        if self.set_motion_params():
            # TODO: Need the proper uom from the driver?
            self.setDriver(driver, myint(value))
            return True
        self.l_error("set_motion_param","failed to set %s=%s" % (param,value) )
        return False


    def set_motion_linkage(self, driver=None, param=None, value=None):
        self.l_debug("set_motion_linkage","driver={0} param={1} value={2}".format(driver,param,value))
        if not self.is_responding():
            return False
        if value is None:
            self.l_error("set_motion_linkage","not passed a value: %s" % (value) )
            return False
        if param is None:
            self.l_error("set_motion_linkage","not passed a param: %s" % (param) )
            return False
        if not param in linkage_bits:
            self.l_error("set_motion_linkage unknown param '%s'" % (param) )
            return False
        value = int(value)
        if 'linkage' in self.cam_status['motion_detect']:
            self.get_cam_motion_detect_config(report=False)
            cval = int(self.cam_status['motion_detect']['linkage'])
            self.l_debug("set_motion_linkage","param=%s value=%s, bit=%d, motion_detect_linkage=%s" % (param,value,linkage_bits[param],cval))
            if value == 0:
                cval = clearBit(cval,linkage_bits[param])
            else:
                cval = setBit(cval,linkage_bits[param])
            # TODO: Should use the _driver specified function instead of int.
            self.cam_status['motion_detect']['linkage'] = cval
            self.l_debug("set_motion_linkage","%d" % (cval))
            if self.set_motion_params():
                self.l_debug("set_motion_linkage","setDriver({0},{1})".format(driver, myint(value)))
                self.setDriver(driver, myint(value))
                return True
            self.l_error("set_motion_param","failed to set %s=%s" % ("linkage",cval) )
            return False
        else:
            self.l_error("set_motion_param","linkage not found in {}".format(self.cam_status['motion_detect']))
            return False

    def cmd_reboot(self, command):
        """ Reboot the Camera """
        if not self.is_responding():
            return False
        return self._http_get("reboot.cgi",{})

    def cmd_goto_preset(self, command):
        """ Goto the specified preset. """
        value = command.get("value")
        if not self.is_responding():
            return False
        if value is None:
            self.l_error("_goto_preset not passed a value: %s" % (value) )
            return False
        if not self.http_get("ptzGotoPresetPoint",{"name": int(value)}):
            self.l_error("cmd_goto_preset","failed to set %s" % (int(value)) )
        return True

    def cmd_set_almoa(self,command):
        self.set_motion_param('GV6','isEnable',command.get("value"))

    def cmd_set_mo_mail(self,command):
        self.set_motion_linkage('GV7','send_mail',command.get("value"))

    def cmd_set_almos(self,command):
        self.set_motion_param('GV8','sensitivity',command.get("value"))

    def cmd_set_mo_trig(self,command):
        self.set_motion_param('GV10','triggerInterval',command.get("value"))

    def cmd_set_mo_ring(self,command):
        self.set_motion_linkage('GV0','ring',command.get("value"))

    def cmd_set_mo_pic(self,command):
        self.set_motion_linkage('GV14','snap_picture',command.get("value"))

    def cmd_set_mo_push(self,command):
        self.set_motion_linkage('GV15','push',command.get("value"))

    def cmd_set_mo_rec(self,command):
        self.set_motion_linkage('GV4','record',command.get("value"))

    def cmd_set_mo_pic_int(self,command):
        self.set_motion_param('GV13','snapInterval',command.get("value"))

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
        {'driver': 'GV14', 'value': 0,  'uom': 2},  # Motion Picture
        {'driver': 'GV15', 'value': 0,  'uom': 2}   # Push To Phone
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
        'SET_MO_PUSH':    cmd_set_mo_push,    # GV15
        'SET_POS':        cmd_goto_preset,
        'REBOOT':         cmd_reboot,
    }
