# for managing a local arp cache

import time
import logging
import subprocess
import threading
import shlex

################################################################################
class ArpCache():

    cmdLock = None
    cacheLock = None

    cache = None
    timeout = 0
    arp = None

    #---------------------------------------------------------------------------
    def __init__(self, timeout=5, arp='/usr/sbin/arp -a'):
        self.logger = logging.getLogger('Plugin.arp.ArpCache')
        self.timeout = timeout

        self.cmdLock = threading.Lock()
        self.cacheLock = threading.RLock()

        self.cache = dict()

        self.arp = arp
        self.logger.debug('using command: %s', self.arp)

    #---------------------------------------------------------------------------
    def _normalizeAddress(self, address):
        addr = address.upper()

        # TODO make sure all octets are padded
        # TODO return None for invalid address

        return addr

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        self.cacheLock.acquire()

        self.updateCurrentDevices()
        self.purgeInactiveDevices()

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def _getRawArpTable(self):
        if self.arp is None: return None

        # the command takes some time to run so we will bail if
        # another thread is already executing the arp command
        if not self.cmdLock.acquire(False):
            self.logger.warn('arp: already in use')
            return None

        cmd = shlex.split(self.arp)
        self.logger.debug('exec: %s', cmd)

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pout, perr = proc.communicate()
        except:
            pout = None

        self.cmdLock.release()

        return pout

    #---------------------------------------------------------------------------
    def updateCurrentDevices(self):
        rawOutput = self._getRawArpTable()
        if rawOutput is None: return

        self.cacheLock.acquire()

        # translate command output to cache entries
        for line in rawOutput.splitlines():
            parts = line.split()
            if len(parts) < 4: continue

            addr = self._normalizeAddress(parts[3])
            if addr is None: continue

            self.cache[addr] = time.time()
            self.logger.debug('device found: %s', addr)

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def purgeInactiveDevices(self):
        toBePurged = list()

        self.cacheLock.acquire()

        # first, find all the expired keys
        for addr in self.cache.keys():
            if not self.isActive(addr):
                self.logger.debug('device expired: %s; marked for removal', addr)
                toBePurged.append(addr)

        # now, delete the expired addresses
        for addr in toBePurged: del self.cache[addr]

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def isActive(self, address):
        addr = self._normalizeAddress(address)

        last = self.cache.get(addr)
        if last is None: return False

        now = time.time()
        diff = (now - last) / 60

        self.logger.debug('device %s last activity was %d min ago', address, diff)

        return (diff < self.timeout)

    #---------------------------------------------------------------------------
    def getActiveDeviceCount(self):
        return len(self.cache)

