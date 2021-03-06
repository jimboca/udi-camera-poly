
import polyinterface
from camera_funcs import myint

class Motion(polyinterface.Node):
    """ Node that monitors motion """

    def __init__(self, controller, parent, primary):
        name    = primary.name    + "-Motion"
        address = primary.address + "m";
        self.pnode = primary
        self.motion_st  = 0
        super(Motion, self).__init__(controller, primary.address, address, name)

    def start(self):
        self.query()

    def query(self):
        """ query the motion status camera """
        # pylint: disable=unused-argument
        self.pnode.l_debug("Motion:query:","...")
        cm = self.pnode.get_motion_status()
        if cm != self.motion_st:
            self.motion_st = cm
            self.setDriver('ST', self.motion_st)
        self.pnode.l_debug("Motion:query:"," ST=%s" % (self.motion_st))
        if cm == 3:
            return False
        return True

    def motion(self, value):
        """ motion detected on the camera, set the status so we start poling """
        self.motion_st = int(value)
        self.pnode.l_debug("Motion:motion:","Motion==%s" % (self.motion_st))
        self.pnode.set_motion_status(self.motion_st)
        return self.setDriver('ST', self.motion_st)

    def shortPoll(self):
        """ 
        poll called by polyglot 
        - If motion is on then query the camera to see if it's still on
        """
        #self.pnode.l_debug("Motion:poll:%s: Motion=%d" % (self.name,self.motion_st))
        if self.motion_st == 1:
            self.pnode.l_info("Motion:poll","Check Motion")
            self.query()
        return True

    def longPoll(self):
        """
        Motion doesn't do long poll cause the camera handles it
        """
        self.pnode.l_info("Motion:long_poll:%s:" % (self.name))
        # Only check motion if it's unknown
        if self.motion_st == 2:
            self.pnode.l_info("Motion:long_poll","Check Motion")
            self.query()
        return True
    
    drivers = [
        {'driver': 'ST',   'value': 0,  'uom': 25}, # ST: Motion on/off
    ]
    commands = {
        'QUERY': query,
    }
    # The nodeDef id of this camers.
    id = 'CamMotion'
