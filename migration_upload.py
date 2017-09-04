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

HOST_NAME = 'https://aws.door43.org/'
RETRY_FAILURES = False
DESTINATION_FOLDER = '../ConvertedDokuWiki'
access_token = None


def get_url(url):
    """
    :param str|unicode url: URL to open
    :param bool catch_exception: If <True> catches all exceptions and returns <False>
    :return tuple of file contents and header Link
    """
    headers = {
        'Authorization': 'token ' + access_token
    }

    response = requests.get(url, headers=headers)
    return response


def upload_repos():

    url = HOST_NAME + 'api/v1/photonomad0/repos'
    # url = HOST_NAME + 'api/v1/user/repos'
    # url = HOST_NAME + 'api/v1/repos/search?q=php&uid=0&limit=75'
    # response = get_url(url)

    isRepoPresent('photonomad', '')

def isRepoPresent(user, repo):
    url = HOST_NAME + 'api/v1/repos/search?q={0}&uid={1}'.format(repo, user)
    response = get_url(url)
    list = json.loads(response.text)
    return list

def upload_obs(lang):
    return True

if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    access_token = file_utils.read_file("gogs_api_token")
    upload_repos()
