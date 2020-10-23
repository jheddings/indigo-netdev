## handle client activities for Network Devices

import logging
import shlex
import json
import socket
import urllib2
import threading
import subprocess

from ssl import SSLError
from urllib2 import URLError

################################################################################
class ClientBase():

    #---------------------------------------------------------------------------
    def __init__(self):
        self.logger = logging.getLogger('Plugin.client.ClientBase')
        self.execLock = threading.Lock()

    #---------------------------------------------------------------------------
    # defined here as a convenience to subclasses
    def _exec(self, *cmd):
        self.execLock.acquire()
        self.logger.debug(u'=> exec%s', cmd)

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        retval = proc.returncode
        self.logger.debug(u'=> exit(%d)', retval)

        # TODO check perr
        #self.logger.warn(perr)

        self.execLock.release()
        return (retval == 0)

    #---------------------------------------------------------------------------
    def isAvailable(self): raise NotImplementedError()

################################################################################
class NullClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self):
        ClientBase.__init__(self)

    #---------------------------------------------------------------------------
    def isAvailable(self):
        return False

################################################################################
class LocalCommand(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, statusCommand='/usr/bin/true'):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.LocalCommand')

        self.statusCommand = statusCommand

    #---------------------------------------------------------------------------
    def isAvailable(self):
        statusCmd = self.statusCommand
        self.logger.debug(u'checking status: %s', statusCmd)

        if statusCmd is None:
            return False
        else:
            cmd = shlex.split(statusCmd)
            return self._exec(*cmd)

################################################################################
class ServiceClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, address, port):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.ServiceClient')

        self.address = address
        self.port = port

    #---------------------------------------------------------------------------
    # determine if the specific host is reachable
    def isAvailable(self):
        self.logger.debug('checking host - %s:%d', self.address, self.port)

        ret = True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect( (self.address, self.port) )
            sock.close()
        except:
            ret = False

        return ret

################################################################################
class PingClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, address):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.PingClient')
        self.address = address

    #---------------------------------------------------------------------------
    # determine if the specific host is reachable
    def isAvailable(self):
        self.logger.debug('pinging address - %s', self.address)

        # we will only wait for 1 ping response
        cmd = ['/sbin/ping', '-c1', self.address]

        return self._exec(*cmd)

################################################################################
class HttpClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, url):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.HttpClient')
        self.url = url

    #---------------------------------------------------------------------------
    # determine if the returned status code is success or error
    def isAvailable(self):
        self.logger.debug('connecting to URL - %s', self.url)
        available = None

        try:
            resp = urllib2.urlopen(self.url)
            status = resp.getcode()

            self.logger.debug('HTTP status - %d', status)
            available = (200 <= status <= 299)

            # XXX how are redirects handled?

        except Exception as e:
            self.logger.warn(str(e))
            available = False

        # XXX maybe we want to return None (Error) for 5xx codes?

        return available

################################################################################
class ArpClient(ClientBase):

    # NOTE we depend on the ARP table to be maintained outside this client

    #---------------------------------------------------------------------------
    def __init__(self, address, arpTable):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.ArpClient')

        self.address = address
        self.arpTable = arpTable

    #---------------------------------------------------------------------------
    # check for the device in the current ARP table
    def isAvailable(self):
        self.logger.debug('checking ARP table for device - %s', self.address)
        return self.arpTable.isActive(self.address)

################################################################################
class ExternalAddressClient(ClientBase):

    # helper class for parsing API results...
    # based on API at https://www.ipify.org/

    #---------------------------------------------------------------------------
    def __init__(self):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.ExternalAddressClient')

        current_address = None

    #---------------------------------------------------------------------------
    def parseAddress(self, url):
        self.logger.debug('getting address from API - %s', url)

        try:
            resp = urllib2.urlopen(url)
            raw = resp.read()
            self.logger.debug('read %d bytes from API', len(raw))

            data = json.loads(raw)
            addr = data['ip']

        except SSLError as e:
            self.logger.error('SSLError - %s', e.reason)
            addr = None

        except URLError as e:
            self.logger.error('URLError - %s', e.reason)
            addr = None

        self.current_address = addr

        return addr

################################################################################
class IPv4AddressClient(ExternalAddressClient):

    #---------------------------------------------------------------------------
    def __init__(self):
        ExternalAddressClient.__init__(self)
        self.logger = logging.getLogger('Plugin.client.IPv4AddressClient')

    #---------------------------------------------------------------------------
    def isAvailable(self):
        addr = self.parseAddress('https://api.ipify.org/?format=json')
        self.logger.debug('found external address - %s', addr)
        return addr is not None

################################################################################
class IPv6AddressClient(ExternalAddressClient):

    #---------------------------------------------------------------------------
    def __init__(self):
        ExternalAddressClient.__init__(self)
        self.logger = logging.getLogger('Plugin.client.IPv6AddressClient')

    #---------------------------------------------------------------------------
    def isAvailable(self):
        addr = self.parseAddress('https://api6.ipify.org/?format=json')
        self.logger.debug('found external address - %s', addr)
        return addr is not None

################################################################################
class SSHClient(ServiceClient):

    # FIXME not a big fan of the "commands" dictionary...
    # commands contain user-defined instructions for specific actions:
    # - status : determine if the system is available
    # - shutdown : shut the system down; halt; power off

    #---------------------------------------------------------------------------
    def __init__(self, address, port=22, username=None, password=None):
        ServiceClient.__init__(self, address, port)
        self.logger = logging.getLogger('Plugin.client.SSHClient')

        self.commands = dict()
        self.username = username
        self.password = password

    #---------------------------------------------------------------------------
    def isAvailable(self):
        statusCmd = self.commands.get('status', None)
        self.logger.debug(u'checking remote status: %s', statusCmd)

        if statusCmd is None:
            return ServiceClient.isAvailable(self)
        else:
            cmd = shlex.split(statusCmd)
            return self._rexec(*cmd)

    #---------------------------------------------------------------------------
    def turnOff(self):
        shutdownCmd = self.commands.get('shutdown', None)
        self.logger.debug(u'=> %s', shutdownCmd)
        if shutdownCmd is None: return False

        # execute the command remotely
        cmd = shlex.split(shutdownCmd)
        status = self._rexec(*cmd)

        return status

    #---------------------------------------------------------------------------
    def _rexec(self, *cmd):
        # setup the remote command using a safe ssh config
        # XXX -f would be ideal, but we lose the return code of the remote command
        rcmd = ['/usr/bin/ssh', '-anTxq']

        # TODO support global timeout, e.g.
        #rcmd.append('-o', 'ConnectTimeout=%d' % connectionTimeout)

        # username is optional for SSH commands...
        username = self.username
        if username is not None and len(username) > 0:
            self.logger.debug(u'running as remote user: %s', username)
            rcmd.extend(('-l', username))
        else:
            # TODO capture local username in debug log
            self.logger.debug(u'running as local user')

        # add the host and port
        rcmd.extend(('-p', str(self.port), self.address))

        # add all commands supplied by caller
        rcmd.extend(cmd)

        return self._exec(*rcmd)

