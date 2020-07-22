# provides wrapper objects for specific device types

import logging
import urllib2
import time

import arp
import clients
import iplug

# TODO set setErrorStateOnServer(msg) appropriately

################################################################################
# wrapper base class for device types
class DeviceWrapper():

    #---------------------------------------------------------------------------
    def __init__(self, device):
        raise NotImplementedError()

    #---------------------------------------------------------------------------
    # basic check to see if the virtual device is responding
    def updateStatus(self):
        device = self.device

        if self.client.isAvailable():
            self.logger.debug(u'%s is AVAILABLE', device.name)
            device.updateStateOnServer('active', True)
            device.updateStateOnServer('status', 'Active')
            device.updateStateOnServer('lastActiveAt', time.strftime('%c'))

        else:
            self.logger.debug(u'%s is UNAVAILABLE', device.name)
            device.updateStateOnServer('active', False)
            device.updateStateOnServer('status', 'Inactive')

        self.updateDeviceInfo()

    #---------------------------------------------------------------------------
    # sub-classes should overide this for their custom states
    def updateDeviceInfo(self): pass

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        pass

################################################################################
# base wrapper class for relay-type devices
class RelayDeviceWrapper(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        raise NotImplementedError()

    #---------------------------------------------------------------------------
    # default behavior; subclasses should provide correct implementation
    def turnOff(self):
        self.logger.warn(u'Not supported - Turn Off %s', self.device.name)

    #---------------------------------------------------------------------------
    # default behavior; subclasses should provide correct implementation
    def turnOn(self):
        self.logger.warn(u'Not supported - Turn On %s', self.device.name)

    #---------------------------------------------------------------------------
    # basic check to see if the virtual device is responding
    def updateStatus(self):
        device = self.device

        if self.client.isAvailable():
            self.logger.debug(u'%s is AVAILABLE', device.name)
            device.updateStateOnServer('onOffState', 'on')
        else:
            self.logger.debug(u'%s is UNAVAILABLE', device.name)
            device.updateStateOnServer('onOffState', 'off')

        self.updateDeviceInfo()

################################################################################
# plugin device wrapper for Network Service devices
class Service(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        self.logger = logging.getLogger('Plugin.wrapper.Service')

        address = device.pluginProps['address']
        port = int(device.pluginProps['port'])
        client = clients.ServiceClient(address, port)

        self.device = device
        self.client = client

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        iplug.validateConfig_Hostname('address', values, errors, emptyOk=False)
        iplug.validateConfig_Int('port', values, errors, min=1, max=65536)

################################################################################
# plugin device wrapper for Ping Status devices
class Ping(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        self.logger = logging.getLogger('Plugin.wrapper.Ping')

        address = device.pluginProps['address']

        self.device = device
        self.client = clients.PingClient(address)

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        iplug.validateConfig_Hostname('address', values, errors, emptyOk=False)

################################################################################
# plugin device wrapper for External IP devices
class ExternalIP(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        self.logger = logging.getLogger('Plugin.wrapper.ExternalIP')

        addressType = device.pluginProps['addressType']

        self.device = device

        if addressType == 'ipv4':
            self.client = clients.IPv4AddressClient()
        elif addressType == 'ipv6':
            self.client = clients.IPv6AddressClient()

    #---------------------------------------------------------------------------
    def updateDeviceInfo(self):
        # the worker (client) keeps a record of the current address...
        addr = self.client.current_address

        device = self.device

        props = device.pluginProps
        props['address'] = addr
        device.replacePluginPropsOnServer(props)

        if addr is not None:
            device.updateStateOnServer('lastKnownAddress', addr)

################################################################################
# plugin device wrapper for HTTP Status devices
class HTTP(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        self.logger = logging.getLogger('Plugin.wrapper.HTTP')

        url = device.pluginProps['url']

        self.device = device
        self.client = clients.HttpClient(url)

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        iplug.validateConfig_URL('url', values, errors, emptyOk=False)

        # update 'address' for proper display
        url = values['url']
        req = urllib2.Request(url)

        values['address'] = req.get_host()

################################################################################
# plugin device wrapper for Local Device types
class Local(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device, arpTable):
        self.logger = logging.getLogger('Plugin.wrapper.Local')

        address = device.pluginProps['address']

        self.device = device
        self.client = clients.ArpClient(address, arpTable)

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        iplug.validateConfig_MAC('address', values, errors, emptyOk=False)

################################################################################
# plugin device wrapper for SSH Device types
class SSH(RelayDeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        self.logger = logging.getLogger('Plugin.wrapper.SSH')

        address = device.pluginProps['address']
        port = int(device.pluginProps['port'])
        uname = device.pluginProps['username']
        client = clients.SSHClient(address, port=port, username=uname)

        client.commands['status'] = device.pluginProps['cmd_status']
        client.commands['shutdown'] = device.pluginProps['cmd_shutdown']

        self.client = client
        self.device = device

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        iplug.validateConfig_Hostname('address', values, errors, emptyOk=False)
        iplug.validateConfig_Int('port', values, errors, min=1, max=65536)

        iplug.validateConfig_String('username', values, errors, emptyOk=False)
        #iplug.validateConfig_String('password', values, errors, emptyOk=True)

        iplug.validateConfig_String('cmd_status', values, errors, emptyOk=False)
        iplug.validateConfig_String('cmd_shutdown', values, errors, emptyOk=False)

    #---------------------------------------------------------------------------
    def turnOff(self):
        device = self.device
        self.logger.info(u'Shutting down %s', device.name)

        if not self.client.turnOff():
            self.logger.error(u'Could not turn off remote server: %s', device.name)

################################################################################
# plugin device wrapper for macOS Device types
class macOS(RelayDeviceWrapper):

    # XXX could we use remote management instead of SSH?

    #---------------------------------------------------------------------------
    def __init__(self, device):
        self.logger = logging.getLogger('Plugin.wrapper.macOS')

        address = device.pluginProps['address']
        uname = device.pluginProps.get('username', None)
        passwd = device.pluginProps.get('password', None)
        client = clients.SSHClient(address, username=uname, password=passwd)

        # macOS commands are known and cannot be changed by the user
        client.commands['status'] = '/usr/bin/true'
        client.commands['shutdown'] = '/sbin/shutdown -h now'

        self.client = client
        self.device = device

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        iplug.validateConfig_Hostname('address', values, errors, emptyOk=False)
        iplug.validateConfig_String('username', values, errors, emptyOk=False)
        #iplug.validateConfig_String('password', values, errors, emptyOk=True)

