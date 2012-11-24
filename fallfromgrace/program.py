# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import os
import psutil
import re
import signal
import time
import yaml

log = logging.getLogger('fall-from-grace')


class Monitor(object):
    def __init__(self):
        self.name = None
        self.cmdline = None
        self.actions = None


class Trigger(object):
    def __init__(self, s):
        self.s = s

    def evaluate(self, env):
        # TODO (bjorn): Make more robust!

        tokens = self.s.split()
        new = []
        for tok in tokens:
            val = tok
            if val in env:
                val = env[val]
            new.append(val)
        if not len(new) == 3:
            return False
        #log.debug('new: %s', new)
        if new[1] == '>':
            return new[0] > int(new[2])


class ConfigException(Exception):
    pass


class Configuration(object):
    def __init__(self):
        self.monitor = None

    def validate_trigger(self, trigger):
        trig = Trigger(trigger)
        trig.evaluate({'rmem': 0, 'vmem': 0})

    def load(self, yaml_str):
        try:
            conf = yaml.load(yaml_str)
        except Exception, e:
            log.error('failed to read config file: %s', e)
            return

        monitor = []

        for name, monitor_conf in conf.iteritems():
            if not 'cmdline' in monitor_conf:
                raise ConfigException('failed to read config file: %s has no "cmdline"' % name)
            if 'actions' not in monitor_conf:
                raise ConfigException('failed to read config file: %s has no "actions"' % name)

            if not monitor_conf['actions']:
                raise ConfigException('failed to read config file: %s has no "actions"' % name)

            try:
                cmdline = re.compile(monitor_conf['cmdline'])
            except Exception, e:
                raise ConfigException('failed to compile cmdline %r: %s' % (cmdline, e))

            for trigger, action in monitor_conf['actions'].iteritems():
                if action not in ['term']:
                    raise ConfigException('invalid action: %s' % action)
                try:
                    self.validate_trigger(trigger)
                except Exception, e:
                    raise ConfigException('invalid trigger: %s - %s' % (trigger, e))

            m = Monitor()
            m.name = name
            m.cmdline = cmdline
            m.actions = monitor_conf['actions']
            monitor.append(m)

        # success
        self.monitor = monitor

    def load_from_file(self):
        try:
            self.load(file('/etc/fall-from-grace.conf', 'r').read())
        except Exception, e:
            log.error('failed to read config file: %s', e)
            return


class FallFromGrace(object):
    """Main program class."""

    SLEEP_TIME = 10

    def __init__(self, options, args):
        self.options = options
        self.args = args
        self.running = True
        self.config = Configuration()

    def _read_conf(self):
        try:
            self.config.load_from_file()
        except ConfigException, e:
            log.error('%s', e)
        except Exception, e:
            log.error('unhandled exception from config load: %s', e)

    def _act(self, proc, monitor):
        #log.debug('proc %s monitor %s', proc, monitor)

        env = {}
        env['rmem'], env['vmem'] = proc.get_memory_info()

        for trigger, action in monitor.actions.iteritems():
            eret = Trigger(trigger).evaluate(env)
            if eret:
                log.info('Monitor %s and %s hit, action: %s', monitor.name, trigger, action)
                if action == 'term':
                    os.kill(proc.pid, signal.SIGTERM)

    def run(self):
        log.info('starting up fall-from-grace')
        self._read_conf()

        while self.running:
            # TODO (bjorn): Optimize
            for proc in psutil.get_process_list():
                cmdline = ' '.join(proc.cmdline)
                for monitor in self.config.monitor:
                    if monitor.cmdline.search(cmdline):
                        self._act(proc, monitor)
            time.sleep(self.SLEEP_TIME)

    def shutdown(self, *args):
        log.info('shutting down')
        self.running = False

    def reload(self, *args):
        log.info('reloading')
        self._read_conf()
