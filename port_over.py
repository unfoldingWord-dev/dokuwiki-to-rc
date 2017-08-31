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

import json

import sys
from general_tools import url_utils, file_utils

if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    door43_repos_str = url_utils.get_url('https://api.github.com/users/Door43/repos')
    door43_repo_list = json.loads(door43_repos_str)
    door43_repos = {}
    for repo in door43_repo_list:
        name = repo['name']
        door43_repos[name] = repo

    print(len(door43_repo_list))