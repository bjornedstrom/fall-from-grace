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

    try:
        proc = psutil.Process(pid)
        return ' '.join(proc.cmdline)
    except psutil.NoSuchProcess:
        return None
    except Exception, e:
        log.warning('process exception for pid %s: %s', pid, e)
        return None


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


def get_parent_pids(pid):
    """Returns a list of parent pids, up to pid 1.
    """

    pids = []
    while True:
        proc = psutil.Process(pid)
        pids.append(proc.ppid)
        if proc.ppid <= 1:
            break
        pid = proc.ppid
    return pids


def get_snapshot():
    """Returns a snapshot of currently running processes.

    Specifically, returns (tree, cmdlines) where tree is a dict from
    pid to a set of children, and cmdlines is a dict from pid to
    cmdline.
    """

    tree = {}
    cmdlines = {}
    for proc in psutil.get_process_list():
        try:
            ppid = proc.ppid
        except Exception, e:
            continue
        try:
            cmdline = ' '.join(proc.cmdline)
        except Exception, e:
            continue
        cmdlines[proc.pid] = cmdline
        if ppid not in tree:
            tree[ppid] = set()
        if proc.pid not in tree:
            tree[proc.pid] = set()
        tree[ppid].add(proc.pid)
    return tree, cmdlines


def walk_children(tree, pid):
    """Yields all children of pid given in tree (returned from
    get_snapshot above).
    """

    for cpid in tree[pid]:
        yield cpid
        for ccpid in walk_children(tree, cpid):
            yield ccpid
