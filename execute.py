#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#    Copyright (c) 2016 unfoldingWord
#    http://creativecommons.org/licenses/MIT/
#    See LICENSE file for details.
#
#    Contributors:
#    Phil Hopper <phillip_hopper@wycliffeassociates.org>
#
#    Usage: python execute.py name_of_script_in_cli_dir
#
from __future__ import unicode_literals
import sys

if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    if len(args) > 0:
        cmd = args[0]
        if cmd[-3:] != '.py':
            cmd += '.py'

        with open('cli/' + cmd) as f:
            code = compile(f.read(), cmd, 'exec')
            exec(code)
