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


class FallFromGrace(object):
    """Main program class."""

    SLEEP_TIME = 10

    def __init__(self, options, args):
        self.options = options
        self.args = args
        self.running = True
        self.monitor = []

    def _read_conf(self):
        try:
            conf = yaml.load(file('/etc/fall-from-grace.conf', 'r').read())
        except Exception, e:
            log.error('failed to read config file: %s', e)
            return
        self.monitor = []
        for name, monitor_conf in conf.iteritems():
            m = Monitor()
            m.name = name
            m.cmdline = re.compile(monitor_conf['cmdline'])
            m.actions = monitor_conf['actions']
            self.monitor.append(m)

    def _act(self, proc, monitor):
        #log.debug('proc %s monitor %s', proc, monitor)

        rmem, vmem = proc.get_memory_info()

        def evaluate(rule):
            tokens = rule.split()
            new = []
            for tok in tokens:
                val = tok
                if val == 'rmem':
                    val = rmem
                elif val == 'vmem':
                    val = vmem
                new.append(val)
            if not len(new) == 3:
                return False
            #log.debug('new: %s', new)
            if new[1] == '>':
                return new[0] > int(new[2])

        for trigger, action in monitor.actions.iteritems():
            eret = evaluate(trigger)
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
                for monitor in self.monitor:
                    if monitor.cmdline.search(cmdline):
                        self._act(proc, monitor)
            time.sleep(self.SLEEP_TIME)

    def shutdown(self, *args):
        log.info('shutting down')
        self.running = False

    def reload(self, *args):
        log.info('reloading')
        self._read_conf()
