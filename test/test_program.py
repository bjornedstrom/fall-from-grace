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


if __name__ == '__main__':
    unittest.main()
