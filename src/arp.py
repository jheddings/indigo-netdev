# for managing a local arp cache

import time
import logging
import subprocess
import threading
import shlex
import sys

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
    def __getitem__(self, key): return self.cache.get(key)
    def __setitem__(self, key, value): self.cache[key] = value

    #---------------------------------------------------------------------------
    def _normalizeAddress(self, address):
        addr = address.lower()

        # TODO return None for invalid address

        # make sure all octets are padded - macOS arp does not pad properly
        addr = ':'.join(map(lambda byte: byte.zfill(2), addr.split(':')))

        return addr

    #---------------------------------------------------------------------------
    def _getRawArpOutput(self):
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
    def _updateCacheData(self, arp_output):
        self.logger.debug('reading %d bytes into ARP table', len(arp_output))
        self._updateCacheLines(arp_output.splitlines())

    #---------------------------------------------------------------------------
    def _updateCacheLines(self, lines):
        self.logger.debug('loading %d lines into ARP table', len(lines))

        self.cacheLock.acquire()

        for line in lines:
            self._updateCacheLine(line)

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def _updateCacheLine(self, line):
        self.logger.debug('parsing table entry: %s', line)

        parts = line.split()
        if len(parts) < 4: return

        # XXX safe to assume the part index?
        addr = self._normalizeAddress(parts[3])
        if addr is None: return

        self.cacheLock.acquire()

        # update time for found devices
        tstamp = time.time()
        self.cache[addr] = tstamp
        self.logger.debug('device found: %s @ %s', addr, tstamp)

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def _isExpired(self, timestamp):
        if timestamp is None: return None

        # configured timeout is in minutes, timestamps are in seconds...

        now = time.time()
        diff = (now - timestamp) / 60

        return (diff >= self.timeout)

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        self.cacheLock.acquire()

        self.updateCurrentDevices()
        self.purgeExpiredDevices()

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def updateCurrentDevices(self):
        rawOutput = self._getRawArpOutput()
        if rawOutput is None: return

        self._updateCacheData(rawOutput)

    #---------------------------------------------------------------------------
    def purgeExpiredDevices(self):
        # track the items that have expired...  we can't modify
        # the cache while we are iterating over its contents
        expiredDevices = list()

        self.cacheLock.acquire()

        # first, find all the expired keys
        for addr, tstamp in self.cache.items():
            if self._isExpired(tstamp):
                self.logger.debug('device expired: %s; marked for removal', addr)
                expiredDevices.append(addr)

        # now, delete the expired addresses
        for addr in expiredDevices: del self.cache[addr]

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def isActive(self, address):
        addr = self._normalizeAddress(address)
        tstamp = self.cache.get(addr)

        self.logger.debug('device %s expires @ %s', addr, tstamp)

        expired = self._isExpired(tstamp)
        if expired is None: return False

        return (not expired)

    #---------------------------------------------------------------------------
    def getActiveDeviceCount(self):
        count = 0

        self.cacheLock.acquire()

        for addr, tstamp in self.cache.items():
            if not self._isExpired(tstamp):
                count += 1

        self.cacheLock.release()

        return count

################################################################################
def main():
    table = sys.stdin.read()

    # TODO if there is a command line param, use that to build the arp table

    arp = ArpCache(arp=None)
    arp._updateCacheData(table)

#-------------------------------------------------------------------------------
if (__name__== "__main__"):
    logging.basicConfig(level=logging.DEBUG)
    main()
