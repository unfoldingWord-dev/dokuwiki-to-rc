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

from src import file_utils

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

        repair_language_migrations(DESTINATION_ORG, lang_folder)


def repair_language_migrations(org, lang, ignore_if_exists=False):
    print("checking " + lang)
    success = repair_migration(org, lang, 'obs', ignore_if_exists=ignore_if_exists)
    success2 = repair_migration(org, lang, 'tq', ignore_if_exists=ignore_if_exists)
    # success3 = upload_migration(org, lang, 'tw', ignore_if_exists=ignore_if_exists)
    success4 = repair_migration(org, lang, 'tn', ignore_if_exists=ignore_if_exists)
    success = success or success2 or success4
    if not success:
        print("language migration failed for " + lang)
        return False

def repair_migration(org, lang, type, ignore_if_exists=False):
    source_repo_name = os.path.join(MIGRATION_FOLDER, lang, type)
    if not os.path.exists(source_repo_name):
        # print("Migrated repo {0} not found".format(source_repo_name))
        return False

    print("checking " + source_repo_name)

    destination_repo_name = lang + '_obs'
    if type != 'obs':
        destination_repo_name += '-' + type

    upload_results_file = os.path.join(source_repo_name, '..', type + '_upload.json')
    upload = is_uploaded(upload_results_file, source_repo_name, org, destination_repo_name)
    if not upload:
        return False

    manifest_file = os.path.join(source_repo_name, 'manifest.yaml')
    if not os.path.isfile(manifest_file):
        print("Manifest for repo {0} not found".format(source_repo_name))
        return False

    manifest = file_utils.load_yaml_object(manifest_file)
    if 'dublin_core' in manifest:
        core = manifest['dublin_core']
        if 'language' in core:
            language = core['language']
            if 'identifier' in language:
                identifier = language['identifier']
                if (identifier != lang):
                    language['identifier'] = lang
                    file_utils.write_file(manifest_file, manifest)

            success = make_sure_git_updated(source_repo_name, upload_results_file)
            if not success:
                print("Failed to update repo {0}".format(source_repo_name))
            return success

    print("Nothing to update")
    return True


def refresh_git_repo(changed, untracked, source_repo_name, upload_results_file, no_push=False):
    print("Found uncommitted changes")

    if untracked:
        success = run_git(['add', '-A', '.'], source_repo_name)
        if not success:
            error_log(upload_results_file, "git add {0} failed".format(source_repo_name))
            return False

    if untracked or changed:
        success = run_git(['add', '.'], source_repo_name)
        if not success:
            error_log(upload_results_file, "git add {0} failed".format(source_repo_name))

        success = run_git(['commit', '-m "repair language code in manifest"'], source_repo_name)
        if not success:
            error_log(upload_results_file, "git commit {0} failed".format(source_repo_name))
            return False

        if not no_push:
            success = run_git(['push', 'origin', 'master'], source_repo_name)
            if not success:
                error_log(upload_results_file, "git commit {0} failed".format(source_repo_name))
                return False

    return True


def update_local_git_repo(source_repo_name, upload_results_file):
    print("Updating local repo: {0}".format(source_repo_name))
    changed, untracked = is_git_changed(source_repo_name)
    if changed:
        refresh_git_repo(changed, untracked, source_repo_name, upload_results_file, no_push=True)

    success = run_git(['pull', 'origin', 'master'], source_repo_name)
    if not success:
        error_log(upload_results_file, "git commit {0} failed".format(source_repo_name))
        return False

    return True


def is_uploaded(upload_results_file, source_repo_name, org, destination_repo_name):
    try:
        previous_upload_results = file_utils.load_json_object(upload_results_file)
        if not previous_upload_results:

            # double check in case uploaded without results
            repo_exists = isRepoPresent(HOST_NAME, org, destination_repo_name, gogs_access_token)
            if repo_exists:
                print("already uploaded")
                success = make_sure_git_updated_from_repo(source_repo_name, upload_results_file)
                if not success:
                    print("failed to update, no .git?")
                    return False
                return True
            return False

        success = previous_upload_results and previous_upload_results['success']
        if success:
            repo_exists = isRepoPresent(HOST_NAME, org, destination_repo_name, gogs_access_token)
            if repo_exists:
                print("already uploaded")
                make_sure_git_updated_from_repo(source_repo_name, upload_results_file)
                return True
            else:
                print("upload missing, ignore")

    except:
        pass

    return False

def make_sure_git_updated_from_repo(source_repo_name, upload_results_file):
    git_exists = os.path.exists(os.path.join(source_repo_name, '.git'))
    if git_exists:
        return update_local_git_repo(source_repo_name, upload_results_file)
    return git_exists


def make_sure_git_updated(source_repo_name, upload_results_file):
    git_exists = os.path.exists(os.path.join(source_repo_name, '.git'))
    if git_exists:
        changed, untracked = is_git_changed(source_repo_name)
        if changed:
            return refresh_git_repo(changed, untracked, source_repo_name, upload_results_file)
        return True
    return False

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
