# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import mock
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
        self.assertEquals(False, config.monitor[0].check_children)

    def test_config_sigstop_success(self):
        config = ffg.Configuration()

        config.load("""# for conkeror
conkeror:
  cmdline: xulrunner-bin .*conkeror
  actions:
    rmem > 1073741824: stop @ 2m
""")

        self.assertEquals(['stop', '@', 120], config.monitor[0].actions[0][1].action_list)

    def test_config_children_success(self):
        config = ffg.Configuration()

        config.load("""# for conkeror
conkeror:
  cmdline: xulrunner-bin .*conkeror
  children: True
  actions:
    rmem > 1073741824: term
""")

        self.assertEquals(True, config.monitor[0].check_children)

    def test_config_final_success(self):
        config = ffg.Configuration()

        config.load("""# for conkeror
conkeror:
  cmdline: xulrunner-bin .*conkeror
  final: True
  actions:
    rmem > 1073741824: term
""")

        self.assertEquals(True, config.monitor[0].final)

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
        self.assertEquals(2253, ffg.Trigger('2.2k < rmem').expr[0])
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


class FallFromGraceProgramTest(unittest.TestCase):
    def setUp(self):
        class MockedFFG(ffg.FallFromGrace):
            SLEEP_TIME = 1

            def _read_conf(self):
                self.config.load("""conkeror:
  cmdline: xulrunner-bin .*conkeror
  final: 1
  actions:
    rmem > 1g: term

conkeror2:
  cmdline: xulrunner-bin .*conkeror
  final: 1
  actions:
    rmem > 2g: kill

firefox:
  cmdline: firefox$
  actions:
    rmem > 700m: exec@60s notify-send "$NAME ($PID) is using too much ram"
    rmem > 900m: term

firefox2:
  cmdline: firefox2$
  children: 1
  actions:
    rmem > 1.2g: stop @ 2m
""")

        self.grace = MockedFFG(None, None)
        self.grace._testing = True

    @mock.patch('os.kill')
    @mock.patch('subprocess.call')
    @mock.patch('fallfromgrace.process.get_snapshot')
    @mock.patch('fallfromgrace.process.get_memory_usage')
    def test_program(self, get_memory_usage, get_snapshot, call, kill):
        get_memory_usage.return_value = {'rmem': 300*1024*1024,
                                         'vmem': 300*1024*1024}
        get_snapshot.return_value = {1220: set()}, {1220: 'foo'}

        self.grace.run()

        self.assertEquals(False, call.called)
        self.assertEquals(False, kill.called)

        get_snapshot.return_value = {1220: set()}, {1220: 'firefox'}
        get_memory_usage.return_value = {'rmem': 800*1024*1024,
                                         'vmem': 300*1024*1024}

        self.grace.run()

        call.assert_called_with('notify-send "firefox (1220) is using too much ram"', shell=True)

        # new test
        get_memory_usage.return_value = {'rmem': 950*1024*1024,
                                         'vmem': 300*1024*1024}

        self.grace.run()

        kill.assert_called_with(1220, signal.SIGTERM)

        # new test
        get_snapshot.return_value = {4443: set()}, {4443: 'firefox2'}
        get_memory_usage.return_value = {'rmem': 1500*1024*1024,
                                         'vmem': 300*1024*1024}

        self.grace.run()

        kill.assert_called_with(4443, signal.SIGSTOP)

        # new test
        kill.called = False
        call.called = False

        self.grace._tick()

        self.assertEquals(False, kill.called)
        self.assertEquals(False, call.called)

        # test "final"
        get_memory_usage.return_value = {'rmem': 2400*1024*1024,
                                         'vmem': 300*1024*1024}
        get_snapshot.return_value = {4443: set()}, {4443: 'xulrunner-bin /usr/share/conkeror'}
        kill.called = False
        call.called = False

        self.grace.run()

        kill.assert_called_with(4443, signal.SIGTERM)

    # TODO (bjorn): Below test is very hacky
    @mock.patch('os.kill')
    @mock.patch('fallfromgrace.process.get_snapshot')
    def test_children(self, get_snapshot, kill):
        get_snapshot.return_value = {4443: set([5555]), 5555: set()}, {4443: 'firefox2', 5555: 'subproc'}

        get_memory_usage_orig = ffg.process.get_memory_usage

        def fake_memusage(pid):
            if pid == 4443:
                return {'rmem': 300*1024*1024,
                        'vmem': 300*1024*1024}
            elif pid == 5555:
                return {'rmem': 1500*1024*1024,
                        'vmem': 300*1024*1024}
        ffg.process.get_memory_usage = fake_memusage

        try:
            self.grace.run()

            kill.assert_called_with(5555, signal.SIGSTOP)
        finally:
            ffg.process.get_memory_usage = get_memory_usage_orig


if __name__ == '__main__':
    unittest.main()
