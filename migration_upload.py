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
# Upload all converted OBS repos on github.com/Door43 from DokuWiki to Resource containers in ../ConvertedDokuWiki
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
import subprocess
from general_tools import file_utils
from general_tools.file_utils import write_file

HOST_NAME = 'https://aws.door43.org'
RETRY_FAILURES = False
MIGRATION_FOLDER = '../ConvertedDokuWiki'
DESTINATION_ORG = 'DokuWiki'
access_token = None


def get_url(url):
    """
    :param str|unicode url: URL to open
    :return response
    """
    headers = {
        'Authorization': 'token ' + access_token
    }

    response = requests.get(url, headers=headers)
    return response


def post_url(url, data):
    """
    :param str|unicode url: URL to open
    :param bool catch_exception: If <True> catches all exceptions and returns <False>
    :return tuple of file contents and header Link
    """
    headers = {
        'Authorization': 'token ' + access_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(url, data, headers=headers)
    return response


def upload_repos():

    upload_language_migrations(DESTINATION_ORG, 'en')

    # url = HOST_NAME + '/api/v1/repos/Door43/repos'
    # # url = HOST_NAME + '/api/v1/user/repos'
    # # url = HOST_NAME + '/api/v1/repos/search?q=php&uid=0&limit=75'
    # # response = get_url(url)
    #
    # found1 = isRepoPresent(DESTINATION_ORG, 'en-obs')
    # found2 = isRepoPresent(DESTINATION_ORG, 'en-obs2')
    # found3 = createRepoInOrganization(DESTINATION_ORG, 'en-obs2')
    # found4 = isRepoPresent(DESTINATION_ORG, 'en-obs2')


def upload_language_migrations(org, lang, ignore_if_exists=False):
    print("migrating " + lang)
    success = upload_migration(org, lang, 'obs', ignore_if_exists=ignore_if_exists)
    success = success or upload_migration(org, lang, 'tq', ignore_if_exists=ignore_if_exists)
    # success = success or upload_migration(org, lang, 'tw', ignore_if_exists=ignore_if_exists)
    success = success or upload_migration(org, lang, 'tn', ignore_if_exists=ignore_if_exists)
    if not success:
        print("language migration failed for " + lang)
        return False

def upload_migration(org, lang, type, ignore_if_exists=False):
    source_repo_name = os.path.join(MIGRATION_FOLDER, lang, type)
    print("migrating " + source_repo_name)
    if not os.path.exists(source_repo_name):
        print("Migrated repo {0} not found".format(source_repo_name))
        return False

    destination_repo_name = lang + '_obs'
    if type != 'obs':
        destination_repo_name += '-' + type

    results_file = os.path.join(source_repo_name, '..', type + '_upload.json')
    upload = is_upload_needed(results_file, source_repo_name)
    if not upload:
        return False

    repo_exists = isRepoPresent(org, destination_repo_name)
    if not repo_exists:
        created = createRepoInOrganization(org, destination_repo_name)
        print("Creating Repo {0}/{1}".format(org, destination_repo_name))
        if not created:
            error_log(results_file, "Repo {0}/{1} creation failure".format(org, destination_repo_name))
            return False
    elif not ignore_if_exists:
        error_log(results_file, "Repo {0}/{1} already exists".format(org, destination_repo_name))
        return False

    success = run_git(['init', '.'], source_repo_name)
    if not success:
        error_log(results_file, "git init {0} failed".format(source_repo_name))
        return False

    success = run_git(['add', '.'], source_repo_name)
    if not success:
        error_log(results_file, "git add {0} failed".format(source_repo_name))
        return False

    success = run_git(['commit', '-m "first commit"'], source_repo_name)
    if not success:
        error_log(results_file, "git commit {0} failed".format(source_repo_name))
        return False

    remote_repo = 'https://git.door43.org/DokuWiki/{0}.git'.format(destination_repo_name)
    success = run_git(['remote', 'add', 'origin', remote_repo], source_repo_name)
    if not success:
        error_log(results_file, "git commit {0} failed".format(source_repo_name))
        return False

    success = run_git(['push', 'origin', 'master'], source_repo_name)
    if not success:
        error_log(results_file, "git commit {0} failed".format(source_repo_name))
        return False

    save_success(results_file)
    return True


def is_upload_needed(results_file, source_repo_name, retry_on_error=False):
    try:
        content_path = os.path.join(source_repo_name, 'content')
        if not os.path.exists(content_path):
            print("skipping since no content")
            return False

        previous_results = file_utils.load_json_object(results_file)
        success = previous_results['success']
        if success:
            print("already uploaded")
            return False

        if not retry_on_error:
            error = 'unknown' if 'error' not in previous_results else previous_results['error']
            print("Skipping due to previous upload error: " + error)
            return False

    except:
        pass

    return True


def error_log(results_file, msg):
    data = {
        'success': False,
        'error': msg
    }
    save_results(results_file, data)
    print("ERROR: " + msg)


def save_success(results_file):
    data = {
        'success': True
    }
    save_results(results_file, data)


def save_results(results_file, data):
    write_file(results_file, data)


def run_git(params, working_folder):
    print("Doing git {0}".format(params[0]))
    initial_dir = os.path.abspath(os.curdir)
    os.chdir(working_folder)
    command = ['git'] + params
    results = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success = results.returncode == 0
    os.chdir(initial_dir)  # restore curdir
    return success


def isRepoPresent(user, repo):
    url = HOST_NAME + '/api/v1/repos/{0}/{1}'.format(user, repo)
    response = get_url(url)
    text = response.text
    if not text:
        return False
    results = json.loads(text)
    return results and (len(results) > 0)


def createRepoInOrganization(org, repo):
    """
    Note that user must be the same as the user for access_token
    :param user:
    :param repo:
    :return:
    """
    url = '{0}/api/v1/org/{1}/repos'.format(HOST_NAME, org)
    data = 'name={0}'.format(repo)
    response = post_url(url, data)
    text = response.text
    if text:
        results = json.loads(text)
        if results and 'full_name' in results:
            full_name = '{0}/{1}'.format(org, repo)
            return results['full_name'] == full_name
    return False


def createRepoForCurrentUser(repo):
    """
    :param repo:
    :return:
    """
    url = HOST_NAME + '/api/v1/user/repos'
    data = 'name={0}'.format(repo)
    response = post_url(url, data)
    text = response.text
    if text:
        results = json.loads(text)
        if results and 'full_name' in results:
            full_name = '{0}/{1}'.format(user, repo)
            return results['full_name'] == full_name
    return False

def upload_obs(lang):
    return True

if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    access_token = file_utils.read_file("gogs_api_token")
    upload_repos()
