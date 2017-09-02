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
import sys
from general_tools import file_utils

DESTINATION_FOLDER = '../ConvertedDokuWiki'
RELOAD = False


def get_results_summary():
    out_dir = DESTINATION_FOLDER
    results_file = os.path.join(out_dir, "results.json")
    repo_results = file_utils.load_json_object(results_file)

    if RELOAD:
        lang_folders = [f for f in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, f))]
        for folder in lang_folders:

            # get obs results
            path = os.path.join(out_dir, folder, "obs_results.json")
            results = file_utils.load_json_object(path)
            if results:
                name = results['name'] + '_obs'
                repo_results[name] = results

            # get tw results
            path = os.path.join(out_dir, folder, "tw_results.json")
            results = file_utils.load_json_object(path)
            if results:
                name = results['name'] + '_tw'
                repo_results[name] = results

        file_utils.write_file(results_file, repo_results)

    if repo_results:
        print("\nFound {0} items".format(len(repo_results)))

        obs_converted_success = []
        obs_converted_error_misc = []
        obs_converted_error_missing = []
        obs_converted_error_not_converted = []
        tw_converted_success = []
        tw_converted_error_misc = []
        tw_converted_error_missing = []
        tw_converted_error_obs_failed = []

        keys = list(repo_results.keys())
        keys.sort()
        for k in keys:
            if k.find("_obs") >= 0:
                value = repo_results[k]
                del repo_results[k]
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

            if k.find("_tw") >= 0:
                value = repo_results[k]
                del repo_results[k]
                success = get_key(value, 'tw_success', False)
                error = get_key(value, 'tw_error', None)

                if success:
                    tw_converted_success.append(value)

                elif error:
                    if error.find('Downloading kt file names') >= 0:
                        tw_converted_error_missing.append(value)

                    elif error.find('Skipping over TW since OBS Failed') >= 0:
                        tw_converted_error_obs_failed.append(value)

                    else:
                        tw_converted_error_misc.append(value)

                else:
                    tw_converted_error_misc.append(value)

        print_results_list('OBS Successes', obs_converted_success, 'obs_error')
        print_results_list('OBS Missing front/back', obs_converted_error_missing, 'obs_error')
        print_results_list('OBS Title Not Translated', obs_converted_error_not_converted, 'obs_error')
        print_results_list('OBS Other Errors', obs_converted_error_misc, 'obs_error', detail=True)
        print_results_list('TW Successes', tw_converted_success, 'tw_error')
        print_results_list('TW missing files', tw_converted_error_missing, 'tw_error')
        print_results_list('TW failed OBS', tw_converted_error_obs_failed, 'tw_error')
        print_results_list('TW Other Errors', tw_converted_error_misc, 'tw_error', detail=True)

    print_results_dict('Unrecognized items', repo_results, 'error', detail=True)


def print_results_dict(msg, results_list, error_key, detail=False):
    names = list(results_list.keys())
    print("\n{0} {1}: {2}".format(len(names), msg, ','.join(names)))

    if detail:
        for name in names:
            item = results_list[name]
            error = get_key(item, error_key, None)
            if not error:
                error = json.dumps(item)
            print("\n   {0}: {1}".format(item['name'], error))

def print_results_list(msg, results_list, error_key, detail=False):
    names = [x['name'] for x in results_list]
    print("\n{0} {1}: {2}".format(len(names), msg, ','.join(names)))

    if detail:
        for item in results_list:
            error = get_key(item, error_key, None)
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
