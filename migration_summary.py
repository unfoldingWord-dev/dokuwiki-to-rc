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
# show summary of all OBS migrations and uploads in ../ConvertedDokuWiki
#   The intent here is to see if there are any failures that are not expected
#
# setup: get token from door43.org and save in file 'gogs_api_token'
#  use applications to get a token
####################################################################################################

from __future__ import unicode_literals

import json
import os
import sys
import requests
from general_tools import file_utils
from converters.common import isRepoPresent, is_git_changed

DESTINATION_FOLDER = '../ConvertedDokuWiki'
HOST_NAME = 'https://aws.door43.org'
DESTINATION_ORG = 'DokuWiki'
RELOAD = False  # set to True to refresh master list from each conversion summary in DESTINATION_FOLDER
gogs_access_token = None

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

    if RELOAD or not repo_results:
        if not repo_results:
            repo_results = {}

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

            # get tq results
            path = os.path.join(out_dir, folder, "tq_results.json")
            results = file_utils.load_json_object(path)
            if results:
                name = results['name'] + '_tq'
                repo_results[name] = results

            # get tn results
            path = os.path.join(out_dir, folder, "tn_results.json")
            results = file_utils.load_json_object(path)
            if results:
                name = results['name'] + '_tn'
                repo_results[name] = results

        file_utils.write_file(results_file, repo_results)

    show_migration_results(repo_results)
    show_upload_results(out_dir)

upload_successes = []
upload_failures = []

def show_upload_results(out_dir):
    lang_folders = [f for f in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, f))]
    for lang in lang_folders:
        print("lang: " + lang)
        validate_repo(out_dir, lang, 'obs')
        validate_repo(out_dir, lang, 'tq')
        validate_repo(out_dir, lang, 'tn')

    print_results_list('Upload Successes', upload_successes, 'error')
    print_results_list('Upload Failures', upload_failures, 'error', detail=True)

def validate_repo(out_dir, lang, type):
    lang_folder = os.path.join(out_dir, lang)
    source_repo_path = os.path.join(lang_folder, type)

    destination_repo_name = lang + '_obs'
    if type != 'obs':
        destination_repo_name += '-' + type

    convert_results_file = os.path.join(lang_folder, type + "_results.json")
    convert_success_key = type + "_success"
    convert_results = file_utils.load_json_object(convert_results_file)
    convert_success = convert_results and (convert_success_key in convert_results) \
                      and convert_results[convert_success_key]

    if not convert_success:
        return False  # only care if convert succeeded

    changed = False
    untracked = False
    repo_exists = isRepoPresent(HOST_NAME, DESTINATION_ORG, destination_repo_name, gogs_access_token)
    if repo_exists:
        git_init = os.path.exists(os.path.join(source_repo_path, ".git"))
        if git_init:
            changed, untracked = is_git_changed(source_repo_path)

    if changed:
        return save_error(destination_repo_name, "Has uncommited git changes")

    upload_results_file = os.path.join(lang_folder, type + "_upload.json")
    upload_results = file_utils.load_json_object(upload_results_file)
    upload_success = upload_results and ('success' in upload_results) and upload_results['success']

    error = ''
    if not upload_success and upload_results and ('error' in upload_results):
        error = upload_results['error']

        # remove invalid error
        if error and (error.find('already exists') >= 0):
            upload_results['success'] = True
            upload_results['error'] = None
            file_utils.write_file(upload_results_file, upload_results)
            upload_success = True
            error = ''

    if upload_success:
        if repo_exists:
            return upload_successes.append( { 'name': destination_repo_name, 'success': True } )
        else:
            return save_error(destination_repo_name, "Repo not uploaded")

    return save_error(destination_repo_name, error)


def save_error(name, msg):
    if not msg:
        msg = 'UNKNOWN'
    upload_failures.append( { 'name': name, 'success': False, 'error': msg } )
    return False


def get_url(url):
    """
    :param str|unicode url: URL to open
    :return response
    """
    headers = {
        'Authorization': 'token ' + gogs_access_token
    }

    response = requests.get(url, headers=headers)
    return response


def show_migration_results(repo_results):
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

    gogs_access_token = file_utils.read_file("gogs_api_token")
    get_results_summary()
