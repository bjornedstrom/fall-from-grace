# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import signal
import unittest

import fallfromgrace.program as ffg

log = logging.getLogger('fall-from-grace')
log.addHandler(logging.StreamHandler())


class MockAction(ffg.Action):
    def _do_exec(self, prog):
        self._did = ('exec', prog)

    def _do_signal(self, pid, sig):
        self._did = ('signal', pid, sig)


class FallFromGraceTest(unittest.TestCase):
    def test_config_success(self):
        config = ffg.Configuration()

        config.load("""# for conkeror
conkeror:
  cmdline: xulrunner-bin .*conkeror
  actions:
    rmem > 1073741824: term
""")

        self.assertEquals('conkeror', config.monitor[0].name)

    def test_config_fail(self):
        config = ffg.Configuration()

        self.assertRaises(ffg.ConfigException, lambda: config.load("""
conkeror:
  cmdlin3e: xulrunner-bin .*conkeror
  actions:
    rmem > 1073741824: term
"""))

    def test_trigger_success(self):
        self.assertEquals(True,
                          ffg.Trigger('rmem   <123').evaluate({
                    'rmem': 122,
                    'vmem': 0}))

        self.assertEquals(False,
                          ffg.Trigger('rmem< 123').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

        self.assertEquals(True,
                          ffg.Trigger('rmem<=123').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

        self.assertEquals(True,
                          ffg.Trigger('123   <=  rmem').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

        self.assertEquals(True,
                          ffg.Trigger('120 < rmem').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

        self.assertEquals(True,
                          ffg.Trigger('123 >= rmem').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

        self.assertEquals(False,
                          ffg.Trigger('120 > rmem').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

    def test_trigger_fail(self):
        self.assertRaises(ffg.ConfigException, lambda: ffg.Trigger('! 1230').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

        self.assertRaises(ffg.ConfigException, lambda: ffg.Trigger('120 > rmem').evaluate({
                    'rmem': '123b',
                    'vmem': 0}))

    def test_integer_parse(self):

        self.assertEquals(0, ffg.Trigger('0 < rmem').expr[0])
        self.assertEquals(1, ffg.Trigger('1 < rmem').expr[0])
        self.assertEquals(234, ffg.Trigger('234 < rmem').expr[0])
        self.assertEquals(2048, ffg.Trigger('2k < rmem').expr[0])
        self.assertEquals(123*1024*1024, ffg.Trigger('123m < rmem').expr[0])
        self.assertEquals(123*1024*1024, ffg.Trigger('123M < rmem').expr[0])

        self.assertRaises(Exception, lambda: ffg.Trigger('123c < rmem').expr[0])
        self.assertRaises(Exception, lambda: ffg.Trigger(' < rmem').expr[0])
        self.assertRaises(Exception, lambda: ffg.Trigger('r4 < rmem').expr[0])

    def test_action(self):
        monitor = ffg.Monitor()
        monitor.name = 'foo'
        action = MockAction('term')
        action.action(0, 'bar')
        self.assertEquals(('signal', 0, signal.SIGTERM), action._did)

        action = MockAction('kill')
        action.action(31337, 'bar')
        self.assertEquals(('signal', 31337, signal.SIGKILL), action._did)

        action = MockAction('exec testprogram')
        action.action(31337, 'bar')
        self.assertEquals(('exec', 'testprogram'), action._did)

        action = MockAction('exec testprogram $PID')
        action.action(31337, 'bar')
        self.assertEquals(('exec', 'testprogram 31337'), action._did)

        action = MockAction('exec testprogram $NAME')
        action.action(31337, 'bar')
        self.assertEquals(('exec', 'testprogram bar'), action._did)

        action = MockAction('exec@2m testprogram $PID')
        action.action(31337, 'bar')
        self.assertEquals(('exec', 'testprogram 31337'), action._did)
        action._did = None
        action.action(31337, 'bar')
        self.assertEquals(None, action._did)

        action = MockAction('exec @ 1h testprogram $PID')
        action.action(31337, 'bar')
        self.assertEquals(('exec', 'testprogram 31337'), action._did)

        self.assertRaises(Exception, lambda: MockAction('fexec @ 1h testprogram $PID'))


if __name__ == '__main__':
    unittest.main()
