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
# Upload all migrated Resource containers in ../ConvertedDokuWiki up to door43.org/DokuWiki
#
# setup: get token from door43.org and save in file 'gogs_api_token'
#  use applications to get a token
####################################################################################################

from __future__ import unicode_literals

import os
import sys
from general_tools import file_utils
from general_tools.file_utils import write_file
from converters.common import run_git, is_git_changed, isRepoPresent, createRepoInOrganization

HOST_NAME = 'https://aws.door43.org'
RETRY_FAILURES = False
MIGRATION_FOLDER = '../ConvertedDokuWiki'
DESTINATION_ORG = 'DokuWiki'
gogs_access_token = None
UPLOAD_RETRY_ON_ERROR = True


def upload_repos():

    lang_folders = [f for f in os.listdir(MIGRATION_FOLDER) if os.path.isdir(os.path.join(MIGRATION_FOLDER, f))]
    lang_folders.sort()
    for lang_folder in lang_folders:

        # if lang_folder != 'af':
        #     continue

        upload_language_migrations(DESTINATION_ORG, lang_folder)


def upload_language_migrations(org, lang, ignore_if_exists=False):
    print("migrating " + lang)
    success = upload_migration(org, lang, 'obs', ignore_if_exists=ignore_if_exists)
    success2 = upload_migration(org, lang, 'tq', ignore_if_exists=ignore_if_exists)
    # success3 = upload_migration(org, lang, 'tw', ignore_if_exists=ignore_if_exists)
    success4 = upload_migration(org, lang, 'tn', ignore_if_exists=ignore_if_exists)
    success = success or success2 or success4
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

    upload_results_file = os.path.join(source_repo_name, '..', type + '_upload.json')
    convert_results_file = os.path.join(source_repo_name, '..', type + '_results.json')
    upload = is_upload_needed(upload_results_file, source_repo_name, convert_results_file, org, destination_repo_name, retry_on_error=UPLOAD_RETRY_ON_ERROR)
    if not upload:
        return False

    repo_exists = isRepoPresent(HOST_NAME, org, destination_repo_name, gogs_access_token)
    if not repo_exists:
        created = createRepoInOrganization(HOST_NAME, org, destination_repo_name, gogs_access_token)
        print("Creating Repo {0}/{1}".format(org, destination_repo_name))
        if not created:
            error_log(upload_results_file, "Repo {0}/{1} creation failure".format(org, destination_repo_name))
            return False
    else:  # repo already exists
        git_exists = os.path.exists(os.path.join(source_repo_name, '.git'))
        if git_exists:
            changed, untracked = is_git_changed(source_repo_name)
            if changed:
                return refresh_git_repo(changed, untracked, source_repo_name, upload_results_file)

        if not ignore_if_exists:
            error_log(upload_results_file, "Repo {0}/{1} already exists".format(org, destination_repo_name))
            return False

    success = run_git(['init', '.'], source_repo_name)
    if not success:
        error_log(upload_results_file, "git init {0} failed".format(source_repo_name))
        return False

    success = run_git(['add', '.'], source_repo_name)
    if not success:
        error_log(upload_results_file, "git add {0} failed".format(source_repo_name))
        return False

    success = run_git(['commit', '-m "first commit"'], source_repo_name)
    if not success:
        error_log(upload_results_file, "git commit {0} failed".format(source_repo_name))
        return False

    remote_repo = 'https://git.door43.org/DokuWiki/{0}.git'.format(destination_repo_name)
    success = run_git(['remote', 'add', 'origin', remote_repo], source_repo_name)
    if not success:
        error_log(upload_results_file, "git commit {0} failed".format(source_repo_name))
        return False

    success = run_git(['push', 'origin', 'master'], source_repo_name)
    if not success:
        error_log(upload_results_file, "git commit {0} failed".format(source_repo_name))
        return False

    save_success(upload_results_file)
    return True


def refresh_git_repo(changed, untracked, source_repo_name, upload_results_file):
    print("Found uncommitted changes")

    if untracked:
        success = run_git(['add', '-A', '.'], source_repo_name)
        if not success:
            error_log(upload_results_file, "git add {0} failed".format(source_repo_name))
            return False

    if untracked or changed:
        success = run_git(['commit', '-m "clean up"'], source_repo_name)
        if not success:
            error_log(upload_results_file, "git commit {0} failed".format(source_repo_name))
            return False

        success = run_git(['push', 'origin', 'master'], source_repo_name)
        if not success:
            error_log(upload_results_file, "git commit {0} failed".format(source_repo_name))
            return False

    return True


def is_upload_needed(upload_results_file, source_repo_name, convert_results_file, org, destination_repo_name,
                     retry_on_error=False):
    try:
        content_path = os.path.join(source_repo_name, 'content')
        if not os.path.exists(content_path):
            print("skipping since no content")
            return False

        convert_results = file_utils.load_json_object(convert_results_file)
        basename = os.path.basename(convert_results_file)
        prefix = basename.split('_')
        convert_success_key = prefix[0] + '_' + 'success'
        success = convert_results and (convert_success_key in convert_results) and convert_results[convert_success_key]
        if not success:
            print("skipping failed convert")
            return False

        previous_upload_results = file_utils.load_json_object(upload_results_file)
        if not previous_upload_results:
            return True

        success = previous_upload_results and previous_upload_results['success']
        if success:
            repo_exists = isRepoPresent(HOST_NAME, org, destination_repo_name, gogs_access_token)
            if repo_exists:
                print("already uploaded")
                make_sure_git_updated(source_repo_name, upload_results_file)
                return False
            else:
                print("upload missing, try again")
                return True

        # not success
        error = 'unknown' if 'error' not in previous_upload_results else previous_upload_results['error']
        if not retry_on_error:
            print("Skipping due to previous upload error: " + error)
            return False
        else:
            repo_exists = isRepoPresent(HOST_NAME, org, destination_repo_name, gogs_access_token)
            if not repo_exists:
                print("Retrying Upload, previous upload error: " + error)
                return True

            make_sure_git_updated(source_repo_name, upload_results_file)

    except:
        pass

    return True


def make_sure_git_updated(source_repo_name, upload_results_file):
    git_exists = os.path.exists(os.path.join(source_repo_name, '.git'))
    if git_exists:
        changed, untracked = is_git_changed(source_repo_name)
        if changed:
            refresh_git_repo(changed, untracked, source_repo_name, upload_results_file)


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


if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    gogs_access_token = file_utils.read_file("gogs_api_token")
    upload_repos()
