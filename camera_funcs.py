
import os,socket,struct,json,re,netifaces

def myint(value):
    """ round and convert to int """
    return int(round(float(value)))

def myfloat(value, prec=4):
    """ round and return float """
    return round(float(value), prec)

# from http://commandline.org.uk/python/how-to-find-out-ip-address-in-python/
def get_network_ip_old(remote_server="8.8.8.8",logger=None):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((remote_server, 80))
            rt = s.getsockname()[0]
    except Exception as err:
        logger.error('get_network_ip: failed: {0}'.format(err))
        rt = False
    logger.info('get_network_ip: Returning {0}'.format(rt))
    return rt

def get_network_interface(interface='default',logger=None):
    # Get the default gateway
    gws = netifaces.gateways()
    rt = False
    if interface in gws:
        gwd = gws[interface][netifaces.AF_INET]
        logger.debug("gwd: {}={}".format(interface,gwd))
        ifad = netifaces.ifaddresses(gwd[1])
        rt = ifad[netifaces.AF_INET]
        logger.debug("ifad: {}={}".format(gwd[1],rt))
    else:
        logger.error("No {} in gateways:{}".format(interface,gateways))
    return rt


def get_network_ip(logger=None):
    try:
        iface = get_network_interface(logger=logger)
        rt = iface[0]['addr']
    except Exception as err:
        logger.error('get_network_ip: failed: {0}'.format(err))
        rt = False
    logger.info('get_network_ip: Returning {0}'.format(rt))
    return rt

def get_network_bcast(logger=None):
    try:
        iface = get_network_interface(logger=logger)
        rt = iface[0]['broadcast']
    except Exception as err:
        logger.error('get_network_bcast: failed: {0}'.format(err))
        rt = False
    logger.info('get_network_bcast: Returning {0}'.format(rt))
    return rt

def ip2long(ip):
    """ Convert an IP string to long """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]

def long2ip(value):
    return socket.inet_ntoa(struct.pack('!L', value))


# isBit() returns True or False if bit at offset is set or not
def isBit(int_type, offset):
    mask = 1 << offset
    if (int_type & mask) == 0:
        return False
    return True

# isBit() returns 1 or 0 if bit at offset is set or not
def isBitI(int_type, offset):
    mask = 1 << offset
    if (int_type & mask) == 0:
        return 0
    return 1

# testBit() returns a nonzero result, 2**offset, if the bit at 'offset' is one.
def testBit(int_type, offset):
    mask = 1 << offset
    return(int_type & mask)

# setBit() returns an integer with the bit at 'offset' set to 1.
def setBit(int_type, offset):
    mask = 1 << offset
    return(int_type | mask)

# clearBit() returns an integer with the bit at 'offset' cleared.
def clearBit(int_type, offset):
    mask = ~(1 << offset)
    return(int_type & mask)

# toggleBit() returns an integer with the bit at 'offset' inverted, 0 -> 1 and 1 -> 0.
def toggleBit(int_type, offset):
    mask = 1 << offset
    return(int_type ^ mask)

def str2bool(value):
    """
    Args:
        value - text to be converted to boolean
         True values: y, yes, true, t, on, 1
         False values: n, no, false, off, 0
    """
    return value in ['y', 'yes', 'true', 't', '1']

def bool2int(value):
    if value:
        return 1
    else:
        return 0

def int2str(value):
    if int(value) == 0:
        return "false"
    else:
        return "true"

def str2int(value):
    return bool2int(str2bool(value))

def str_d(value):
    # Only allow utf-8 characters
    #  https://stackoverflow.com/questions/26541968/delete-every-non-utf-8-symbols-froms-string
    return bytes(value, 'utf-8').decode('utf-8','ignore')

# Removes invalid charaters for ISY Node description
def get_valid_node_name(name):

    # Remove <>`~!@#$%^&*(){}[]?/\;:"'` characters from name
    return re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"']+", "", str_d(name))

def get_server_data(logger):
    # Read the SERVER info from the json.
    try:
        with open('server.json') as data:
            serverdata = json.load(data)
    except Exception as err:
        logger.error('harmony_hub_funcs:get_server_data: failed to read hubs file {0}: {1}'.format('server.json',err), exc_info=True)
        return False
    data.close()
    # Get the version info
    try:
        version = serverdata['credits'][0]['version']
    except (KeyError, ValueError):
        logger.info('Version not found in server.json.')
        version = '0.0.0.0'
    # Split version into two floats.
    sv = version.split(".");
    v1 = 0;
    v2 = 0;
    if len(sv) == 1:
        v1 = int(v1[0])
    elif len(sv) > 1:
        v1 = float("%s.%s" % (sv[0],str(sv[1])))
        if len(sv) == 3:
            v2 = int(sv[2])
        else:
            v2 = float("%s.%s" % (sv[2],str(sv[3])))
    serverdata['version'] = version
    serverdata['version_major'] = v1
    serverdata['version_minor'] = v2
    return serverdata

def get_profile_info(logger):
    pvf = 'profile/version.txt'
    try:
        with open(pvf) as f:
            pv = f.read().replace('\n', '')
    except Exception as err:
        logger.error('get_profile_info: failed to read  file {0}: {1}'.format(pvf,err), exc_info=True)
        pv = 0
    f.close()
    return { 'version': pv }
