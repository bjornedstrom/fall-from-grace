# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import re


def unfix(num, fixes):
    """Converts string num with a size postfix, given in dict fixes,
    to an integer.

    unfix('4k', {'k': 1024, 'm': 1024**2}) == 4096
    """
    try:
        fix = None
        if num[-1].lower() in fixes.keys():
            fix = num[-1]
            num = num[:-1]

        mul = 1
        if fix is not None:
            mul = fixes.get(fix.lower(), 1)

        return int(float(num) * mul + 0.5)
    except Exception, e:
        raise ValueError(str(e))


if __name__ == '__main__':
    print unfix('4', {'k': 1024, 'm': 1024**2, 'g': 1024**3})
    print unfix('60m', {'s': 1, 'm': 60, 'h': 60*60})
