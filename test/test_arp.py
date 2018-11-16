#!/usr/bin/env python2.7

import logging
import unittest
import time

import arp

from uuid import getnode

# keep logging output to a minumim for testing
logging.basicConfig(level=logging.ERROR)

################################################################################
class ArpCacheTestBase(unittest.TestCase):

    #---------------------------------------------------------------------------
    def _getLocalMacAddress(self):
        # TODO convert this to octets split by colons
        return hex(getnode())

    #---------------------------------------------------------------------------
    def _buildTableFromCommand(self, cmd):
        cache = arp.ArpCache(arp=cmd)
        cache.rebuildArpCache()
        return cache

    #---------------------------------------------------------------------------
    def _buildTableFromLines(self, lines):
        cache = arp.ArpCache(arp=None)
        cache._updateCacheLines(lines)
        return cache

################################################################################
class ArpCacheContainerTest(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_GetNone(self):
        cache = arp.ArpCache()
        self.assertIsNone(cache['key'])

    #---------------------------------------------------------------------------
    def test_SetGetNone(self):
        cache = arp.ArpCache()
        cache['none'] = None
        self.assertIsNone(cache['none'])

    #---------------------------------------------------------------------------
    def test_BasicSetGetString(self):
        cache = arp.ArpCache()

        cache['key'] = 'value'
        self.assertEqual(cache['key'], 'value')

    #---------------------------------------------------------------------------
    def test_BasicSetGetInt(self):
        cache = arp.ArpCache()

        cache[1] = 42
        self.assertEqual(cache[1], 42)

    #---------------------------------------------------------------------------
    def test_BasicSetGetMixed(self):
        cache = arp.ArpCache()

        cache['key'] = 42
        cache[1] = 'value'

        self.assertEqual(cache['key'], 42)
        self.assertEqual(cache[1], 'value')

################################################################################
class BasicArpCommandUnitTest(ArpCacheTestBase):

    #---------------------------------------------------------------------------
    def test_NullTableUnitTest(self):
        cache = self._buildTableFromCommand(None)
        self.assertEqual(cache.getActiveDeviceCount(), 0)

    #---------------------------------------------------------------------------
    def test_DefaultTableUnitTest(self):
        cache = arp.ArpCache()
        cache.rebuildArpCache()
        self.assertNotEqual(cache.getActiveDeviceCount(), 0)

    #---------------------------------------------------------------------------
    def test_BadReturnValue(self):
        cache = self._buildTableFromCommand('/bin/false')
        self.assertEqual(cache.getActiveDeviceCount(), 0)

    #---------------------------------------------------------------------------
    def test_EmptyTable(self):
        cache = self._buildTableFromCommand('/bin/true')
        self.assertEqual(cache.getActiveDeviceCount(), 0)

    #---------------------------------------------------------------------------
    def test_GarbageOutput(self):
        self._buildTableFromCommand('dd if=/dev/urandom bs=1 count=1024')

################################################################################
class ArpTableParsingUnitTest(ArpCacheTestBase):

    #---------------------------------------------------------------------------
    def test_SimpleArpTableLowerCase(self):
        mac = '20:c4:df:a0:54:28'

        cache = self._buildTableFromLines([
            'localhost (127.0.0.1) at %s on en0 ifscope [ethernet]' % mac
        ])

        self.assertTrue(cache.isActive(mac))
        self.assertTrue(cache.isActive(mac.upper()))

    #---------------------------------------------------------------------------
    def test_SimpleArpTableUpperCase(self):
        mac = '20:C4:D7:A0:54:28'

        cache = self._buildTableFromLines([
            'localhost (127.0.0.1) at %s on en0 ifscope [ethernet]' % mac
        ])

        self.assertTrue(cache.isActive(mac))
        self.assertTrue(cache.isActive(mac.lower()))

    #---------------------------------------------------------------------------
    # seen using DD-WRT routers - slightly different than macOS
    def test_RouterLineFormat(self):
        mac = '30:2A:43:B2:01:2F'

        cache = self._buildTableFromLines([
            'DD-WRT v3.0-r29264 std (c) 2016 NewMedia-NET GmbH',
            '? (10.0.0.1) at %s [ether]  on br0' % mac
        ])

        self.assertTrue(cache.isActive(mac))

    #---------------------------------------------------------------------------
    def test_MultilineBasicTable(self):
        cache = self._buildTableFromLines([
            '? (0.0.0.0) at 11:22:33:44:55:66 on en0 ifscope [ethernet]',
            '? (0.0.0.0) at AA:BB:CC:DD:EE:FF on en0 ifscope [ethernet]',
            '? (0.0.0.0) at 12:34:56:78:9A:BC on en0 ifscope [ethernet]'
        ])

        self.assertTrue(cache.isActive('11:22:33:44:55:66'))
        self.assertTrue(cache.isActive('AA:BB:CC:DD:EE:FF'))
        self.assertTrue(cache.isActive('12:34:56:78:9A:BC'))

    #---------------------------------------------------------------------------
    def test_LeadingZerosInAddressOctects(self):
        cache = self._buildTableFromLines([
            'node (127.0.0.1) at 0:2a:43:4:b:51 on en0 ifscope [ethernet]',
            'node (127.0.0.1) at 20:a2:04:b3:0c:ed on en0 ifscope [ethernet]'
        ])

        self.assertTrue(cache.isActive('0:2a:43:4:b:51'))
        self.assertTrue(cache.isActive('00:2a:43:04:0b:51'))

        self.assertTrue(cache.isActive('20:a2:04:b3:0c:ed'))
        self.assertTrue(cache.isActive('20:a2:4:b3:c:ed'))

################################################################################
class ArpTablePurgeUnitTest(ArpCacheTestBase):

    #---------------------------------------------------------------------------
    def test_ConfirmPurgedItem(self):
        cache = arp.ArpCache(timeout=1, arp=None)

        now = time.time()

        cache['current'] = now
        cache['recent'] = now - 30
        cache['expired'] = now - 61

        cache.purgeExpiredDevices()

        self.assertIn('current', cache.cache);
        self.assertIn('recent', cache.cache);
        self.assertNotIn('expired', cache.cache);

################################################################################
class ArpTableUpdateTest(ArpCacheTestBase):

    # this test relies on internals of the ArpCache, such as directly modifying
    # the contents of the cache and the _update methods

    arp_data = [
        'localhost (127.0.0.1) at 01:23:45:67:89:ab on en0 ifscope [ethernet]',
        'pc (192.168.0.1) at ef:cd:ab:12:34:56 on en0 ifscope [ethernet]',
        'laptop (192.168.0.2) at ab:12:cd:34:ef:56 on en0 ifscope [ethernet]'
    ]

    #---------------------------------------------------------------------------
    def test_BasicUpdateTest(self):
        cache = arp.ArpCache(timeout=1, arp=None)

        cache._updateCacheLines(self.arp_data)

        self.assertTrue(cache.isActive('01:23:45:67:89:ab'));
        self.assertTrue(cache.isActive('ef:cd:ab:12:34:56'));
        self.assertTrue(cache.isActive('ab:12:cd:34:ef:56'));

    #---------------------------------------------------------------------------
    def test_BasicLineUpdateTest(self):
        cache = arp.ArpCache(timeout=1, arp=None)

        cache._updateCacheLine(self.arp_data[0])

        self.assertTrue(cache.isActive('01:23:45:67:89:ab'));
        self.assertFalse(cache.isActive('ef:cd:ab:12:34:56'));
        self.assertFalse(cache.isActive('ab:12:cd:34:ef:56'));

    #---------------------------------------------------------------------------
    def test_LineUpdateTimeShift(self):
        cache = arp.ArpCache(timeout=1, arp=None)

        cache._updateCacheLine(self.arp_data[0])
        first_time = cache['01:23:45:67:89:ab']

        time.sleep(1)

        cache._updateCacheLine(self.arp_data[0])
        second_time = cache['01:23:45:67:89:ab']

        self.assertGreater(second_time, first_time)

################################################################################
class ArpTableActiveExpiredUnitTest(ArpCacheTestBase):

    # this test relies on internals of the ArpCache, such as directly modifying
    # the contents of the cache and the _isExpired method

    #---------------------------------------------------------------------------
    def test_BasicExpirationTests(self):
        cache = arp.ArpCache(timeout=1, arp=None)

        now = time.time()

        self.assertFalse(cache._isExpired(now))
        self.assertFalse(cache._isExpired(now - 30))
        self.assertFalse(cache._isExpired(now - 59))

        self.assertTrue(cache._isExpired(now - 60))
        self.assertTrue(cache._isExpired(now - 500))

    #---------------------------------------------------------------------------
    def test_SimpleCurrentItemCheck(self):
        cache = arp.ArpCache(timeout=1, arp=None)

        now = time.time()

        cache['current'] = now
        cache['recent'] = now - 30

        self.assertTrue(cache.isActive('current'))
        self.assertTrue(cache.isActive('recent'))

    #---------------------------------------------------------------------------
    def test_SimpleExpiredItemCheck(self):
        cache = arp.ArpCache(timeout=1, arp=None)

        now = time.time()

        # since we created the table with a 1-minute timeout...
        cache['expired'] = now - 60
        cache['inactive'] = now - 61
        cache['ancient'] = now - 300

        self.assertFalse(cache.isActive('expired'))
        self.assertFalse(cache.isActive('inactive'))
        self.assertFalse(cache.isActive('ancient'))

