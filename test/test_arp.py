#!/usr/bin/env python2.7

import logging
import unittest

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

################################################################################
class BasicArpTableCommandUnitTest(ArpCacheTestBase):

    #---------------------------------------------------------------------------
    def test_NullTableUnitTest(self):
        cache = self._buildTableFromCommand(None)
        self.assertEqual(cache.getActiveDeviceCount(), 0)

    #---------------------------------------------------------------------------
    def test_DefaultTableUnitTest(self):
        cache = arp.ArpCache()
        cache.rebuildArpCache()
        self.assertNotEqual(cache.getActiveDeviceCount(), 0)

################################################################################
class BadArpTableCommandUnitTest(ArpCacheTestBase):

    # these tests mostly watch for errors when running bad commands

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

