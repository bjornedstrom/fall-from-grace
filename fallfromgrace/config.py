# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import glob
import errno
import logging
import os
import re


log = logging.getLogger('fall-from-grace')
RE_DOT_D_PRIO = re.compile(r'(\d{2})[-]')


def read_dot_d(path):
    """Returns the catenated file contents of a dot d directory.

    Files of the form '^\d{2}-' have a priority given by the
    integer. Files that does not match this defaults to a prio of
    50. Higher prio comes higher in the file.
    """

    files = []
    for filename in os.listdir(path):
        prio_match = RE_DOT_D_PRIO.match(filename)
        prio = None
        if prio_match is not None:
            try:
                prio = int(prio_match.group(1))
            except:
                pass
        full_path = os.path.join(path, filename)
        try:
            content = file(full_path).read()
            if prio is None:
                prio = 50
            files.append((prio, content))
        except IOError, exc:
            if exc.errno == errno.EISDIR:
                pass
            else:
                log.error('cannot read file %s: %s', full_path, exc)
    files.sort()
    return '\n'.join(content for prio, content in reversed(files))


if __name__ == '__main__':
    handler = logging.StreamHandler()
    log.addHandler(handler)
    print read_dot_d('/tmp/test.d')
