#!/usr/bin/env python2.7

import logging
import unittest

import clients

# keep logging output to a minumim for testing
logging.basicConfig(level=logging.ERROR)

################################################################################
class CommonInternetServices(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_GoogleDNS(self):
        client = clients.ServiceClient('8.8.8.8', 53)
        available = client.isAvailable()
        self.assertTrue(available)

################################################################################
class NullClient(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_NullClient(self):
        client = clients.NullClient()
        available = client.isAvailable()
        self.assertFalse(available)

################################################################################
class BasicLocalCommands(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_DefaultCommand(self):
        client = clients.LocalCommand()
        available = client.isAvailable()
        self.assertTrue(available)

################################################################################
class BasicPingTests(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_LocalPing(self):
        client = clients.PingClient('localhost')
        available = client.isAvailable()
        self.assertTrue(available)

    #---------------------------------------------------------------------------
    def test_PingEther(self):
        client = clients.PingClient('0.0.0.0')
        available = client.isAvailable()
        self.assertFalse(available)

################################################################################
class HttpStatusChecks(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_Http200(self):
        client = clients.HttpClient('https://httpstat.us/200')
        available = client.isAvailable()
        self.assertTrue(available)

    #---------------------------------------------------------------------------
    def test_Http301(self):
        client = clients.HttpClient('https://httpstat.us/301')
        available = client.isAvailable()

        # the python client should process the redirect to a "success" status
        self.assertTrue(available)

    #---------------------------------------------------------------------------
    def test_Http404(self):
        client = clients.HttpClient('https://httpstat.us/404')
        available = client.isAvailable()
        self.assertFalse(available)

    #---------------------------------------------------------------------------
    def test_Http500(self):
        client = clients.HttpClient('https://httpstat.us/500')
        available = client.isAvailable()
        self.assertFalse(available)

################################################################################
class LocalHostSSH(unittest.TestCase):

    #---------------------------------------------------------------------------
    def setUp(self):
        self.client = clients.SSHClient('locahost')
        self.client.commands['status'] = '/usr/bin/true'

    #---------------------------------------------------------------------------
    def SKIP_test_isAvailable(self):
        available = self.client.isAvailable()
        self.assertTrue(available)

