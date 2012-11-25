# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import operator
import os
import re
import signal
import time
import yaml

import fallfromgrace.number as number
import fallfromgrace.parser as parser
import fallfromgrace.process as process

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
        try:
            self.expr = parser.parse(expr)
        except Exception, e:
            raise ConfigException('parse error %r: %s' % (expr, e))

    def evaluate(self, env):
        # Set variables
        new = []
        for tok in self.expr:
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
            if action in ['term', 'kill'] or action.startswith('exec'):
                pass
            else:
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
        self.exec_state = {}

    def _read_conf(self):
        try:
            self.config.load_from_file()
        except ConfigException, e:
            log.error('%s', e)
        except Exception, e:
            log.error('unhandled exception from config load: %s', e)

    def _get_environment(self, pid):
        # TODO (bjorn): In the future we may be interested in a more
        # diverse set of variables.
        return process.get_memory_usage(pid)

    def _exec_with_rate_limit(self, pid, monitor, trigger, action):
        exec_at, prog = action.split(' ', 1)
        state_key = '%s %s' % (monitor.name, prog)
        at = None
        last = self.exec_state.get(state_key, 0)

        if '@' in exec_at:
            exec_str, at = exec_at.split('@', 1)
            at = number.unfix(at, {'s': 1,
                                   'm': 60,
                                   'h': 60*60})

        run = False
        if exec_at == 'exec':
            run = True
        elif at is not None:
            if time.time() - last > at:
                run = True

        if run:
            log.info('Monitor %s and %s hit, action: %s', monitor.name, trigger, action)

            prog_expand = prog.replace('$PID', str(pid))
            prog_expand = prog_expand.replace('$NAME', monitor.name)

            # TODO (bjorn): Security implications!!!
            os.system(prog_expand)

            self.exec_state[state_key] = time.time()

    def _act(self, pid, monitor):
        """Maybe do something with the process."""

        #log.debug('proc %s monitor %s', pid, monitor)

        try:
            env = self._get_environment(pid)
        except Exception, e:
            log.warning('failed to get environment for pid %s - %s', pid, e)
            return

        for trigger, action in monitor.actions.iteritems():
            try:
                eret = Trigger(trigger).evaluate(env)
            except Exception, e:
                log.error('failed to evaluate trigger %r: %s', trigger, e)
                continue
            if eret:
                if action in ['term', 'kill']:
                    log.info('Monitor %s and %s hit, action: %s', monitor.name, trigger, action)
                try:
                    if action == 'term':
                        os.kill(pid, signal.SIGTERM)
                    elif action == 'kill':
                        os.kill(pid, signal.SIGKILL)
                    elif action.startswith('exec'):
                        self._exec_with_rate_limit(pid, monitor, trigger, action)
                except Exception, e:
                    log.warning('action failed for %s with %s', pid, e)

    def _tick(self):
        # TODO (bjorn): Optimize
        for pid in process.get_pids():
            cmdline = process.get_cmdline(pid)
            if cmdline is None:
                continue
            for monitor in self.config.monitor:
                if monitor.cmdline.search(cmdline):
                    self._act(pid, monitor)

    def run(self):
        """fall-from-grace main loop."""

        log.info('starting up fall-from-grace')
        self._read_conf()

        while self.running:
            try:
                self._tick()
            except Exception, e:
                log.error('uncaught exception in main loop: %s', e)
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
