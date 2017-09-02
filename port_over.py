#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#    Copyright (c) 2016 unfoldingWord
#    http://creativecommons.org/licenses/MIT/
#    See LICENSE file for details.
#
#    Contributors:
#    Bruce McLean
#
#    Usage: python execute.py name_of_script_in_cli_dir
#

####################################################################################################
#
# setup: copy auth_token.py.example to auth_token.py and edit to set user and toke from github
#  see https://github.com/blog/1509-personal-api-tokens for how to create a token and set the scope to
#    'public_repo'
####################################################################################################

from __future__ import unicode_literals
import json
import os
import sys
import requests
from general_tools import file_utils
from auth_token import get_user_token
from migration.obs_migration import OBS_Migration
from migration.tw_migration import TW_Migration

REPOS_SOURCE = 'https://api.github.com/users/Door43/repos'
RETRY_FAILURES = False
DESTINATION_FOLDER = '../ConvertedDokuWiki'

user_name = None
user_token = None


def get_url(url, catch_exception=False):
    """
    :param str|unicode url: URL to open
    :param bool catch_exception: If <True> catches all exceptions and returns <False>
    :return tuple of file contents and header Link
    """
    if catch_exception:
        # noinspection PyBroadException
        try:
            response = requests.get(url, auth=(user_name, user_token))
        except:
            return None, None
    else:
        response = requests.get(url, auth=(user_name, user_token))

    return response.text, response.links


def get_next_link(links):
    if 'next' in links:
        next = links['next']
        return next['url']
    return None


def convert_door43_repos(source):
    source_url = source
    out_dir = DESTINATION_FOLDER
    file_utils.make_dir(out_dir)
    results_file = os.path.join(out_dir, "results.json")
    door43_repos = {}
    while source_url:
        print("\nOpening: " + source_url + "\n")
        door43_repos_str, link = get_url(source_url)
        door43_repo_list = json.loads(door43_repos_str)
        for repo in door43_repo_list:
            name = repo['name']
            if name[:4] != 'd43-':
                msg = "Skipping over: {0}\n".format(name)
                log_error(results_file, door43_repos, name, msg)
                continue
            data = get_repo_data(name, out_dir, repo)
            if not data:
                msg = "Error getting data for: {0}\n".format(name)
                log_error(results_file, door43_repos, name, msg)
                continue

            for migration_class in [OBS_Migration, TW_Migration]:
                migration = migration_class(data, RETRY_FAILURES)
                migration_name = name + '_' + migration.type
                door43_repos[migration_name] = data
                success = migration.run()
                if migration.final_data:  # update with final data
                    door43_repos[migration_name] = migration.final_data
                file_utils.write_file(results_file, door43_repos)

        source_url = get_next_link(link)
    print(len(door43_repos))


def log_error(results_file, door43_repos, name, msg):
    print('\n' + msg)
    data = {
        'name': name,
        'error': msg
    }
    door43_repos[name] = data
    file_utils.write_file(results_file, door43_repos)


def get_repo_data(name, out_dir, repo):
    contents_url_ = repo['contents_url']
    base_url = contents_url_.replace('{+path}', '')
    parts = name.split('-', 1)
    if len(parts) != 2:
        return None
    lang = parts[1]
    lang_folder = os.path.join(out_dir, lang)
    file_utils.make_dir(lang_folder)
    repo_url = repo['html_url']
    data = {
        'name': name,
        'full_name': repo['full_name'],
        'lc': lang,
        'base_ulr': base_url,
        'repo_url': repo_url,
        'lang_folder': lang_folder
    }
    return data


if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    security = get_user_token().split(':')
    user_name = security[0]
    user_token = security[1]
    convert_door43_repos(REPOS_SOURCE)
