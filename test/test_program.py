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


if __name__ == '__main__':
    unittest.main()
