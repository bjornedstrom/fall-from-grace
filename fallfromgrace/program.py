# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import errno
import logging
import operator
import os
import re
import signal
import subprocess
import time

import fallfromgrace.config
import fallfromgrace.number as number
import fallfromgrace.parser_action as parser_action
import fallfromgrace.parser_trigger as parser_trigger
import fallfromgrace.process as process
import fallfromgrace.orderedyaml as orderedyaml

log = logging.getLogger('fall-from-grace')


class ConfigException(Exception):
    pass


class Monitor(object):
    """Class represents a process to Monitor, i.e. a YAML
    configuration fragment for a process and it's actions.
    """

    def __init__(self):
        # str: Name of the monitor/"rule".
        self.name = None

        # _sre.SRE_Pattern: compiled regex matching on process
        # cmdline.
        self.cmdline = None

        # [(Trigger, Action)]: list of tuples (trigger, action).
        self.actions = None

        # check children?
        self.check_children = False

        # if this monitor triggers, do not consider other monitors.
        self.final = False

    def __repr__(self):
        return '<Monitor name=%r cmdline=%r actions=%r check_children=%r final=%r>' % (
            self.name, self.cmdline, self.actions, self.check_children, self.final)


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
            self.expr = parser_trigger.parse(expr)
        except Exception, e:
            raise ConfigException('parse error %r: %s' % (expr, e))

    def __str__(self):
        return self.s

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


class Action(object):
    """This class represents an action to take on a program.
    """

    def __init__(self, action_str):
        self.action_str = action_str
        self.action_list = parser_action.parse(action_str)

        # TODO (bjorn): Have a global state instead of per-action?
        self.exec_state = {}

    def __str__(self):
        return self.action_str

    def action(self, pid, name):
        """Perform this action on the given pid.

        Will either succeed or log and error.
        """

        what = self.action_list[0]

        try:
            if what == 'exec':
                return self._execute(pid, name)
            elif what == 'kill':
                return self._signal(pid, name, signal.SIGKILL)
            elif what == 'term':
                return self._signal(pid, name, signal.SIGTERM)
            elif what == 'stop':
                return self._signal(pid, name, signal.SIGSTOP)
        except Exception, e:
            log.warning('action failed for %s with %s', pid, e)

    def _execute(self, pid, name):
        prog = self.action_list[-1]
        state_key = '%s %s' % (name, prog)
        at = None
        last = self.exec_state.get(state_key, 0)

        if '@' in self.action_list:
            at = self.action_list[2]

        run = False
        if at is None:
            run = True
        elif at is not None:
            if time.time() - last > at:
                run = True

        if run:
            prog_expand = prog
            prog_expand = prog_expand.replace('$PID', str(pid))
            prog_expand = prog_expand.replace('$NAME', name)

            self._do_exec(prog_expand)

            self.exec_state[state_key] = time.time()

        return run

    def _signal(self, pid, name, sig):
        state_key = '%s %s' % (name, sig)
        at = None
        last = self.exec_state.get(state_key, 0)

        if '@' in self.action_list:
            at = self.action_list[2]

        run = False
        if at is None:
            run = True
        elif at is not None:
            if time.time() - last > at:
                run = True

        if run:
            try:
                self._do_signal(pid, sig)

                self.exec_state[state_key] = time.time()
            except Exception, e:
                # Handle above
                raise

        return run

    def _do_exec(self, prog):
        """Wrapper for unit testing."""

        # TODO (bjorn): Security implications!!!
        subprocess.call(prog, shell=True)

    def _do_signal(self, pid, sig):
        """Wrapper for unit testing."""

        os.kill(pid, sig)


class Configuration(object):
    """A class holding program configuration.

    This attempts to do strict validation of the configuration file
    before committing to the new configs.

    <name>:
      cmdline: <regex>
      actions:
        <Trigger>: <Action>
    """

    def __init__(self):
        # TODO (bjorn): Encapsulate this?
        self.monitor = []

    def validate_trigger(self, trigger):
        trig = Trigger(trigger)
        trig.evaluate({'rmem': 0, 'vmem': 0})

    def validate_action(self, action):
        action = Action(action)

    def load(self, yaml_str):
        """Read config yaml from the string given."""

        conf = orderedyaml.load(yaml_str)
        monitor = []

        for name, monitor_conf in conf.iteritems():
            m = self.load_fragment(name, monitor_conf)
            monitor.append(m)

        # success
        log.info('successfully read config file: monitors %s', ' '.join(m.name for m in monitor))

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
            try:
                self.validate_action(action)
            except Exception, e:
                raise ConfigException('invalid action: %s' % action)
            try:
                self.validate_trigger(trigger)
            except Exception, e:
                raise ConfigException('invalid trigger: %s - %s' % (trigger, e))

        check_children = None
        if 'children' in monitor_conf:
            check_children = monitor_conf['children']

            if check_children not in (True, False):
                raise ConfigException('invalid value for "children", must be boolean')

        final = None
        if 'final' in monitor_conf:
            final = monitor_conf['final']

            if final not in (True, False):
                raise ConfigException('invalid value for "final", must be boolean')

        m = Monitor()
        m.name = name
        m.cmdline = cmdline
        m.actions = []
        if check_children is not None:
            m.check_children = check_children
        if final is not None:
            m.final = final

        for trigger_str, action_str in monitor_conf['actions'].iteritems():
            try:
                trigger = Trigger(trigger_str)
            except Exception, e:
                raise ConfigException('failed to parse trigger %r: %s' % (trigger_str, e))
            try:
                action = Action(action_str)
            except Exception, e:
                raise ConfigException('failed to parse action %r: %s' % (action_str, e))

            m.actions.append((trigger, action))
        return m

    def load_from_file(self):
        """Helper that reads the file in /etc."""

        try:
            conf_data = ''
            try:
                conf_data = file('/etc/fall-from-grace.conf', 'r').read()
            except:
                pass

            dot_d = ''
            try:
                dot_d = fallfromgrace.config.read_dot_d('/etc/fall-from-grace.d')
            except OSError, e:
                if e.errno == errno.ENOENT:
                    pass
            except:
                raise

            conf_cat = '\n'.join([conf_data, dot_d])
            if not conf_cat.strip():
                raise IOError(errno.ENOENT, '/etc/fall-from-grace.conf or /etc/fall-from-grace.d does not exist')

            self.load(conf_cat)
        except Exception, e:
            log.error('failed to read config file: %s', e)
            if self.monitor:
                log.info('using monitors from already read config file: monitors %s',
                         ' '.join(m.name for m in self.monitor))
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

        # TODO (bjorn): A little bit hacky, but aids with
        # unit-testing.
        self._testing = False

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

    def _act(self, pid, monitor):
        """Maybe do something with the process."""

        #log.debug('proc %s monitor %s', pid, monitor)

        try:
            env = self._get_environment(pid)
        except Exception, e:
            log.warning('failed to get environment for pid %s - %s', pid, e)
            return

        for trigger, action in monitor.actions:
            try:
                triggered = trigger.evaluate(env)
            except Exception, e:
                log.error('failed to evaluate trigger %r: %s', trigger, e)
                continue

            if triggered:
                try:
                    did_action = action.action(pid, monitor.name)

                    if did_action:
                        log.info('Monitor %s and %s hit on pid %s, action: %s',
                                 monitor.name, trigger, pid, action)
                except Exception, e:
                    log.error('failed to evaluate action %s: %s', action, e)

    def _tick(self):
        tree, cmdlines = process.get_snapshot()
        for pid, cmdline in cmdlines.iteritems():
            for monitor in self.config.monitor:
                if monitor.cmdline.search(cmdline):
                    self._act(pid, monitor)

                    if monitor.check_children:
                        try:
                            cpids = process.walk_children(tree, pid)
                        except Exception, e:
                            log.warning('failed to get children for pid %s: %s', pid, e)
                        for cpid in cpids:
                            self._act(cpid, monitor)

                    if monitor.final:
                        break

    def run(self):
        """fall-from-grace main loop."""

        log.info('starting up fall-from-grace')
        self._read_conf()

        while self.running:
            try:
                self._tick()
            except Exception, e:
                log.error('uncaught exception in main loop: %s', e)
            if self._testing:
                break
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
