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
import shutil
from general_tools import file_utils

HOST_NAME = 'https://aws.door43.org'
RETRY_FAILURES = False
DESTINATION_FOLDER = '../ConvertedDokuWiki'
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

    url = HOST_NAME + '/api/v1/repos/Door43/repos'
    # url = HOST_NAME + '/api/v1/user/repos'
    # url = HOST_NAME + '/api/v1/repos/search?q=php&uid=0&limit=75'
    # response = get_url(url)

    found1 = isRepoPresent(DESTINATION_ORG, 'en-obs')
    found2 = isRepoPresent(DESTINATION_ORG, 'en-obs2')
    found3 = createRepoInOrganization(DESTINATION_ORG, 'en-obs2')
    found4 = isRepoPresent(DESTINATION_ORG, 'en-obs2')


def upload_migration(lang, type):
    source_repo_name = os.path.join(DESTINATION_FOLDER, lang, type)
    destination_repo_name = lang + '_obs'
    if type != 'obs':
        destination_repo_name += '-' + type


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
