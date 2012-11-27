#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name='fall-from-grace',
      version='0.1.0-rc2',
      description='non-intrusive userspace process supervisor',
      author=u'Björn Edström',
      author_email='be@bjrn.se',
      url='https://github.com/bjornedstrom/fall-from-grace',
      packages=['fallfromgrace'],
      scripts=['bin/fall-from-grace']
     )
