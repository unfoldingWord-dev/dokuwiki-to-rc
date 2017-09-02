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

####################################################################################################
# setup: copy auth_token.py.example to auth_token.py and edit to set user and toke from github
#  see https://github.com/blog/1509-personal-api-tokens for how to create a token and set the scope to
#    'public_repo'
####################################################################################################

from __future__ import unicode_literals

import json
import os
import string

import sys
from general_tools import file_utils

DESTINATION_FOLDER = '../ConvertedDokuWiki'


def get_results_summary():
    out_dir = DESTINATION_FOLDER
    results_file = os.path.join(out_dir, "results.json")
    results = file_utils.load_json_object(results_file)
    if results:
        print("\nFound {0} items".format(len(results)))

        obs_converted_success = []
        obs_converted_error_misc = []
        obs_converted_error_missing = []
        obs_converted_error_not_converted = []

        keys = list(results.keys())
        keys.sort()
        for k in keys:
            if k.find("_obs") >= 0:
                value = results[k]
                del results[k]
                success = get_key(value, 'obs_success', False)
                error = get_key(value, 'obs_error', None)

                if success:
                    obs_converted_success.append(value)

                elif error:
                    if error.find('downloading front and back matter') >= 0:
                        obs_converted_error_missing.append(value)

                    elif error.find('Title not converted error') >= 0:
                        obs_converted_error_not_converted.append(value)

                    else:
                        obs_converted_error_misc.append(value)

                else:
                    obs_converted_error_misc.append(value)

        print_results_list('Successes', obs_converted_success)
        print_results_list('Missing front/back', obs_converted_error_missing)
        print_results_list('Not Converted', obs_converted_error_not_converted)
        print_results_list('Other Errors', obs_converted_error_misc, detail=True)

    print_results_list('Unrecognized items', results)


def print_results_list(msg, results_list, detail=False):
    names = [x['name'] for x in results_list]
    print("{0} {1}: {2}".format(len(names), msg, ','.join(names)))

    if detail:
        for item in results_list:
            error = get_key(item, 'obs_error', None)
            if not error:
                error = json.dumps(item)
            print("\n   {0}: {1}".format(item['name'], error))


def get_key(data, key, default):
    results = default
    if key in data:
        results = data[key]
    return results


if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    get_results_summary()
