# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import psutil

log = logging.getLogger('fall-from-grace')


def get_pids():
    """Yields a snapshot of currently active process ids."""

    for proc in psutil.get_process_list():
        yield proc.pid


def get_cmdline(pid):
    """Returns the cmdline of the given pid."""

    proc = psutil.Process(pid)
    return ' '.join(proc.cmdline)


def get_memory_usage(pid):
    """Returns a dict with memory usage information for the given
    pid. The dict has the following keys:

    "vmem": virtual memory usage,
    "rmem": residential memory usage.
    """

    proc = psutil.Process(pid)
    usage = {}
    usage['rmem'], usage['vmem'] = proc.get_memory_info()
    return usage
