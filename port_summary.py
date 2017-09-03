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

obs_converted_success = []
obs_converted_error_misc = []
obs_converted_error_missing = []
obs_converted_error_not_converted = []
tw_converted_success = []
tw_converted_error_misc = []
tw_converted_error_missing = []
tw_converted_error_obs_failed = []
tq_converted_success = []
tq_converted_error_misc = []
tn_converted_success = []
tn_converted_error_misc = []
tq_converted_error_obs_failed = []
tn_converted_error_obs_failed = []
unsupported_language_error = []


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

        keys = list(repo_results.keys())
        keys.sort()
        for k in keys:
            value = repo_results[k]
            if k.find("_obs") >= 0:
                get_obs_summary(repo_results, k, value)

            elif k.find("_tw") >= 0:
                get_tw_summary(repo_results, k, value)

            elif k.find("_tq") >= 0:
                get_tq_summary(repo_results, k, value)

            elif k.find("_tn") >= 0:
                get_tn_summary(repo_results, k, value)

            else:
                error = get_key(value, 'error', None)
                if error.find('Skipping over unsupported language') >= 0:
                    del repo_results[k]
                    unsupported_language_error.append(value)

        print_results_list('OBS Successes', obs_converted_success, 'obs_error')
        print_results_list('OBS Missing front/back', obs_converted_error_missing, 'obs_error')
        print_results_list('OBS Title Not Translated', obs_converted_error_not_converted, 'obs_error')
        print_results_list('OBS Other Errors', obs_converted_error_misc, 'obs_error', detail=True)
        print_results_list('TW Successes', tw_converted_success, 'tw_error')
        print_results_list('TW missing files', tw_converted_error_missing, 'tw_error')
        print_results_list('TW failed OBS', tw_converted_error_obs_failed, 'tw_error')
        print_results_list('TW Other Errors', tw_converted_error_misc, 'tw_error', detail=True)
        print_results_list('TQ Successes', tq_converted_success, 'tq_error')
        print_results_list('TQ failed OBS', tq_converted_error_obs_failed, 'tq_error')
        print_results_list('TQ Other Errors', tq_converted_error_misc, 'tq_error', detail=True)
        print_results_list('TN Successes', tn_converted_success, 'tn_error')
        print_results_list('TN failed OBS', tn_converted_error_obs_failed, 'tn_error')
        print_results_list('TN Other Errors', tn_converted_error_misc, 'tn_error', detail=True)

    print_results_list('Unsupported language errors', unsupported_language_error, 'error')
    print_results_dict('Unrecognized items', repo_results, 'error', detail=True)


def get_tn_summary(repo_results, key, value):
    del repo_results[key]
    success = get_key(value, 'tn_success', False)
    error = get_key(value, 'tn_error', None)
    if success:
        tn_converted_success.append(value)

    elif error:
        # if error.find('Downloading kt file names') >= 0:
        #     tw_converted_error_missing.append(value)
        #
        if error.find('Skipping over TN since OBS Failed') >= 0:
            tn_converted_error_obs_failed.append(value)

        else:
            tn_converted_error_misc.append(value)

    else:
        tn_converted_error_misc.append(value)


def get_tq_summary(repo_results, key, value):
    del repo_results[key]
    success = get_key(value, 'tq_success', False)
    error = get_key(value, 'tq_error', None)
    if success:
        tq_converted_success.append(value)

    elif error:
        # if error.find('Downloading kt file names') >= 0:
        #     tw_converted_error_missing.append(value)
        #
        if error.find('Skipping over TQ since OBS Failed') >= 0:
            tq_converted_error_obs_failed.append(value)

        else:
            tq_converted_error_misc.append(value)

    else:
        tq_converted_error_misc.append(value)


def get_tw_summary(repo_results, key, value):
    del repo_results[key]
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


def get_obs_summary(repo_results, key, value):
    del repo_results[key]
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
