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
# Convert all OBS repos on github.com/Door43 from DokuWiki to Resource containers in ../ConvertedDokuWiki
# This script keeps track of progress, so it can be restarted if it exits due to communication errors.
#
# setup: get token from github and save in file 'github_api_token'
#  see https://github.com/blog/1509-personal-api-tokens for how to create a token and set the scope to
#    'public_repo'
####################################################################################################

from __future__ import unicode_literals
import json
import os
import sys
import requests
import shutil
from general_tools import file_utils
from migration.obs_migration import OBS_Migration
from migration.tn_migration import TN_Migration
from migration.tq_migration import TQ_Migration
from migration.tw_migration import TW_Migration

REPOS_SOURCE = 'https://api.github.com/users/Door43/repos'
RETRY_FAILURES = True
DESTINATION_FOLDER = '../ConvertedDokuWiki'
github_access_token = None
valid_repos = None
start_page = 0  # repos page to start at


def convert_door43_repos(source):
    source_url = source
    out_dir = DESTINATION_FOLDER
    file_utils.make_dir(out_dir)
    results_file = os.path.join(out_dir, "results.json")
    door43_repos = file_utils.load_json_object(results_file)

    while source_url:
        print("\nOpening: " + source_url + "\n")
        door43_repo_list, link = get_next_page(source_url)
        for repo in door43_repo_list:
            migrate_repo(repo, results_file, door43_repos, out_dir)
        source_url = get_next_link(link)

    print(len(door43_repos))


def get_next_page(source_url):
    params = None
    global start_page
    if start_page:
        params = {'page': str(start_page)}
        start_page = 0
    door43_repos_str, link = get_url(source_url, params=params)
    door43_repo_list = json.loads(door43_repos_str)
    return door43_repo_list, link


def migrate_repo(repo, results_file, door43_repos, out_dir):
    name = repo['name']
    if name[:4] != 'd43-':
        msg = "Skipping over invalid d43 repo name: {0}\n".format(name)
        log_error(results_file, door43_repos, name, msg)
        return

    lang_code = name[4:]

    # if lang_code != 'ceb':
    #     return

    if lang_code not in valid_repos:
        msg = "Skipping over unsupported language: {0}\n".format(name)
        log_error(results_file, door43_repos, name, msg)
        lang_folder = os.path.join(out_dir, lang_code)
        shutil.rmtree(lang_folder, ignore_errors=True)  # make sure nothing left over from previous attempts
        return

    data = get_repo_data(name, out_dir, repo)
    if not data:
        msg = "Error getting data for: {0}\n".format(name)
        log_error(results_file, door43_repos, name, msg)
        return

    print("\nMigrating " + lang_code)

    # for migration_class in [OBS_Migration, TW_Migration, TQ_Migration, TN_Migration]:
    for migration_class in [OBS_Migration, TQ_Migration, TN_Migration]:
        migration = migration_class(data, RETRY_FAILURES)
        migration_name = name + '_' + migration.type
        door43_repos[migration_name] = data
        success = migration.run()
        if migration.final_data:  # update with final data
            door43_repos[migration_name] = migration.final_data
        file_utils.write_file(results_file, door43_repos)


def get_url(url, params=None):
    """
    :param params:
    :param str|unicode url: URL to open
    :return tuple of file contents and header Link
    """

    if not params:
        params = {}

    params['access_token'] = github_access_token

    response = requests.get(url, params=params)
    return response.text, response.links


def get_next_link(links):
    if 'next' in links:
        next = links['next']
        return next['url']
    return None


def log_error(results_file, door43_repos, name, msg):
    print(msg)
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

    valid_repos = file_utils.read_file("valid_repo_list.txt").replace('\r', '').split('\n')
    github_access_token = file_utils.read_file("github_api_token")
    convert_door43_repos(REPOS_SOURCE)
