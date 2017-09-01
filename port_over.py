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
import os
import sys
from contextlib import closing
from general_tools import file_utils
from converters.obs_converter import OBSConverter

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2


def get_url(url, catch_exception=False):
    """
    :param str|unicode url: URL to open
    :param bool catch_exception: If <True> catches all exceptions and returns <False>
    :return tuple of file contents and header Link
    """
    if catch_exception:
        # noinspection PyBroadException
        try:
            with closing(urllib2.urlopen(url)) as request:
                response = request.read()
        except:
            response = False
    else:
        with closing(urllib2.urlopen(url)) as request:
            response = request.read()

    info = request.info()
    link = info.get('Link')  # get Link from headers

    # convert bytes to str (Python 3.5)
    if type(response) is bytes:
        return response.decode('utf-8'), link
    else:
        return response, link


def get_next_link(links):
    link_list = links.split(',')
    for link in link_list:
        parts = link.split(';')
        if parts[1].strip() == 'rel="next"':
            url_str = parts[0]
            url = url_str[1:-1]
            return url
    return None


def convert_door43_repos(source):
    source_url = source
    out_dir = '../ConvertedDokuWiki'
    file_utils.make_dir(out_dir)
    while source_url:
        door43_repos_str, link = get_url(source_url)
        door43_repo_list = json.loads(door43_repos_str)
        door43_repos = {}
        for repo in door43_repo_list:
            name = repo['name']
            data = get_repo_data(name, out_dir, repo)
            door43_repos[name] = data

            convert_obs_if_not(data['lc'], data['lang_folder'], data['repo_url'],name)

        source_url = get_next_link(link)
    print(len(door43_repos))


def get_repo_data(name, out_dir, repo):
    contents_url_ = repo['contents_url']
    base_url = contents_url_.replace('{+path}', '')
    parts = name.split('-')
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


def convert_obs_if_not(lang, lang_folder, repo_url, name):
    obs_folder = os.path.join(lang_folder, 'obs')
    if not os.path.exists(os.path.join(obs_folder, 'content')):
        file_utils.make_dir(obs_folder)

        obs_conv = None
        try:
            obs_conv = OBSConverter(lang, repo_url, obs_folder, False)
            obs_conv.run()
        except Exception as e:
            step = "Init" if not obs_conv else obs_conv.trying
            msg = "Failed doing '" + step + "', error: " + str(e)
            print("\n" + msg)
            return msg
    else:
        print("\nSkipping over already converted OBS in " + name)

    return None


if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    source_url = 'https://api.github.com/users/Door43/repos'
    convert_door43_repos(source_url)
