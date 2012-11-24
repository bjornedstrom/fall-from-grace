# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import operator
import os
import psutil
import re
import signal
import time
import yaml

log = logging.getLogger('fall-from-grace')


class ConfigException(Exception):
    pass


class Monitor(object):
    def __init__(self):
        self.name = None
        self.cmdline = None
        self.actions = None


class Trigger(object):
    """Class implements safe evaluation of some expressions given an
    environment. Currently supports comparison of integers, such as:

    t = Trigger('a < 123')
    True == t.evaluate({'a': 20})
    """

    OPS = {
        '==': operator.eq,
        '<': operator.lt,
        '>': operator.gt,
        '<=': operator.le,
        '>=': operator.ge,
        }

    def __init__(self, expr):
        self.s = expr

    def evaluate(self, env):
        """Given a dict of variables, attempt to evaluate the
        expression given in the expression given in the constructor.

        Will either return a bool or raise ConfigException on a parse
        error.
        """
        # TODO (bjorn): Make more robust!

        tokens = self.s.split()
        if not len(tokens) == 3:
            raise ConfigException('unknown trigger %s' % self.s)

        # Set variables
        new = []
        for tok in tokens:
            val = tok
            if val in env:
                val = env[val]
            new.append(val)

        try:
            op_str = new[1]
            if op_str in self.OPS:
                op_func = self.OPS[op_str]
                return op_func(int(new[0]), int(new[2]))
        except Exception, e:
            raise ConfigException('unknown trigger %s: %s' % (self.s, e))

        raise ConfigException('unknown trigger %s' % self.s)


class Configuration(object):
    """A class holding program configuration.

    This attempts to do strict validation of the configuration file
    before committing to the new configs.
    """

    def __init__(self):
        # TODO (bjorn): Encapsulate this?
        self.monitor = None

    def validate_trigger(self, trigger):
        trig = Trigger(trigger)
        trig.evaluate({'rmem': 0, 'vmem': 0})

    def load(self, yaml_str):
        """Read config yaml from the string given."""

        try:
            conf = yaml.load(yaml_str)
        except Exception, e:
            log.error('failed to read config file: %s', e)
            return

        monitor = []

        for name, monitor_conf in conf.iteritems():
            m = self.load_fragment(name, monitor_conf)
            monitor.append(m)

        # success
        self.monitor = monitor

    def load_fragment(self, name, monitor_conf):
        """Load part of the config file with validation."""

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
            if action not in ['term', 'kill']:
                raise ConfigException('invalid action: %s' % action)
            try:
                self.validate_trigger(trigger)
            except Exception, e:
                raise ConfigException('invalid trigger: %s - %s' % (trigger, e))

        m = Monitor()
        m.name = name
        m.cmdline = cmdline
        m.actions = monitor_conf['actions']
        return m

    def load_from_file(self):
        """Helper that reads the file in /etc."""

        try:
            self.load(file('/etc/fall-from-grace.conf', 'r').read())
        except Exception, e:
            log.error('failed to read config file: %s', e)
            return


class FallFromGrace(object):
    """Main program class for fall-from-grace.

    See README for documentation."""

    # Number of seconds between process enumeration / rule evaluation.
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

    def _get_environment(self, proc):
        # TODO (bjorn): In the future we may be interested in a more
        # diverse set of variables.
        env = {}
        env['rmem'], env['vmem'] = proc.get_memory_info()
        return env

    def _act(self, proc, monitor):
        """Maybe do something with the process."""

        #log.debug('proc %s monitor %s', proc, monitor)

        env = self._get_environment(proc)

        for trigger, action in monitor.actions.iteritems():
            try:
                eret = Trigger(trigger).evaluate(env)
            except Exception, e:
                log.error('failed to evaluate trigger %r: %s', trigger, e)
                continue
            if eret:
                log.info('Monitor %s and %s hit, action: %s', monitor.name, trigger, action)
                if action == 'term':
                    os.kill(proc.pid, signal.SIGTERM)
                elif action == 'kill':
                    os.kill(proc.pid, signal.SIGKILL)

    def _tick(self):
        # TODO (bjorn): Optimize
        for proc in psutil.get_process_list():
            cmdline = ' '.join(proc.cmdline)
            for monitor in self.config.monitor:
                if monitor.cmdline.search(cmdline):
                    self._act(proc, monitor)

    def run(self):
        """fall-from-grace main loop."""

        log.info('starting up fall-from-grace')
        self._read_conf()

        while self.running:
            try:
                self._tick()
            except Exception, e:
                log.error('uncaught exception in main loop: %e', e)
            time.sleep(self.SLEEP_TIME)

    def shutdown(self, *args):
        """Shutdown the program. Bound in the executable to TERM (or
        just any clean shutdown).
        """

        log.info('shutting down')
        self.running = False

    def reload(self, *args):
        """Reload the program configuration file. Bound in the
        executable to SIGHUP.
        """

        log.info('reloading')
        self._read_conf()
