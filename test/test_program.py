# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import unittest

import fallfromgrace.program as ffg

log = logging.getLogger('fall-from-grace')
log.addHandler(logging.StreamHandler())


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
                          ffg.Trigger('rmem < 123').evaluate({
                    'rmem': 122,
                    'vmem': 0}))

        self.assertEquals(False,
                          ffg.Trigger('rmem < 123').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

        self.assertEquals(True,
                          ffg.Trigger('rmem <= 123').evaluate({
                    'rmem': 123,
                    'vmem': 0}))

        self.assertEquals(True,
                          ffg.Trigger('123 <= rmem').evaluate({
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
        trig = ffg.Trigger('rmem < 120')
        parser = lambda x: trig._parse_int(x)

        self.assertEquals(0, parser('0'))
        self.assertEquals(1, parser('1'))
        self.assertEquals(234, parser('234'))
        self.assertEquals(2048, parser('2k'))
        self.assertEquals(123*1024*1024, parser('123m'))
        self.assertEquals(123*1024*1024, parser('123M'))

        self.assertRaises(Exception, lambda: parser('123c'))
        self.assertRaises(Exception, lambda: parser(''))
        self.assertRaises(Exception, lambda: parser('r4'))

if __name__ == '__main__':
    unittest.main()
