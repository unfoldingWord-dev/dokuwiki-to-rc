from __future__ import print_function, unicode_literals
import json
import re
import os
import requests
import subprocess
from collections import OrderedDict
from contextlib import closing
from datetime import datetime
from json import JSONEncoder

# regular expressions for replacing Dokuwiki formatting
h1_re = re.compile(r'====== (.*?) ======', re.UNICODE)
h2_re = re.compile(r'===== (.*?) =====', re.UNICODE)
h3_re = re.compile(r'==== (.*?) ====', re.UNICODE)
h4_re = re.compile(r'=== (.*?) ===', re.UNICODE)
h5_re = re.compile(r'== (.*?) ==', re.UNICODE)
italic_re = re.compile(r'([^:])//(.*?)//', re.UNICODE)
bold_re = re.compile(r'\*\*(.*?)\*\*', re.UNICODE)
image_re = re.compile(r'\{\{(http[s]*:.*?)(\?nolink.*?){0,1}\}\}', re.UNICODE)
link_re = re.compile(r'\[\[(http[s]*:[^:]*)\|(.*?)\]\]', re.UNICODE)
li_re = re.compile(r'^[ ]{1,3}(\* )', re.UNICODE | re.MULTILINE)
li_space_re = re.compile(r'^(\* .*\n)\n(?=\* )', re.UNICODE | re.MULTILINE)
li_last_re = re.compile(r'^(\* .*)\n(?!\* )', re.UNICODE | re.MULTILINE)
ol_re = re.compile(r'^(  - )', re.MULTILINE | re.UNICODE)
over_re = re.compile(r'^( ){6}\*', re.MULTILINE | re.UNICODE)
header_after_nonempty_line_re = re.compile(r'(?<=.\n)(#+ )', re.UNICODE | re.MULTILINE)


def quiet_print(quiet, message, end='\n'):

    if not quiet:
        print(message, end=end)


def dokuwiki_to_markdown(text):
    """
    Cleans up text from possible DokuWiki and HTML tag pollution.
    :param str text:
    :return: str
    """
    text = text.replace('\r', '')
    text = text.replace('\n\n\n\n\n', '\n\n')
    text = text.replace('\n\n\n\n', '\n\n')
    text = text.replace('\n\n\n', '\n\n')
    text = text.replace('\\\\\n', '  \n')
    text = h1_re.sub(r'# \1 #', text)
    text = h2_re.sub(r'## \1 ##', text)
    text = h3_re.sub(r'### \1 ###', text)
    text = h4_re.sub(r'#### \1 ####', text)
    text = h5_re.sub(r'##### \1 #####', text)
    text = ol_re.sub(r'1. ', text)
    text = over_re.sub(r'    *', text)
    text = italic_re.sub(r'\1_\2_', text)
    text = bold_re.sub(r'__\1__', text)
    text = link_re.sub(r'[\2](\1)', text)
    text = image_re.sub(r'![Image](\1)', text)
    text = li_re.sub(r'\1', text)
    text = li_space_re.sub(r'\1', text)
    text = li_last_re.sub(r'\1\n\n', text)
    text = header_after_nonempty_line_re.sub(r'\n\1', text)

    return text


def post_url(url, data):
    """
    :param str|unicode url: URL to open
    :param dict data: The post data
    """

    headers = {'User-Agent': 'Mozilla/5.0',
               'Accept': 'application/json, text/javascript, */*; q=0.01',
               'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
               'X-Requested-With': 'XMLHttpRequest'}

    with closing(requests.Session()) as session:
        response = session.post(url, data=data, headers=headers).content

    # convert bytes to str (Python 3.5)
    if type(response) is bytes:
        return response.decode('utf-8')
    else:
        return response


class ResourceManifest(object):
    def __init__(self, slug, name):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param unicode slug:
        :param unicode name:
        """

        self.syntax_version = '1.0'
        self.type = 'book'
        self.content_mime_type = 'text/markdown'
        self.slug = slug
        self.name = name
        self.versification_slug = 'ufw'
        self.finished_chunks = []
        self.language = {'slug': 'en', 'name': 'English', 'dir': 'ltr'}
        self.status = {'translate_mode': 'all', 'checking_entity': [], 'checking_level': '1', 'version': '4',
                       'comments': '', 'contributors': [], 'pub_date': datetime.today().strftime('%Y-%m-%d'),
                       'license': 'CC BY-SA', 'checks_performed': [],
                       'source_translations': []}

    def __contains__(self, item):
        return item in self.__dict__

    def to_serializable(self):
        return_val = OrderedDict([
            ('syntax_version', self.syntax_version),
            ('type', self.type),
            ('content_mime_type', self.content_mime_type),
            ('language', self.language),
            ('slug', self.slug),
            ('name', self.name),
            ('versification_slug', self.versification_slug),
            ('status', self.status),
            ('finished_chunks', self.finished_chunks)
        ])

        return return_val

class NewResourceManifest(object):
    def __init__(self, slug, name):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param unicode slug:
        :param unicode name:
        """

        self.package_version = '1'
        self.modified_at = int(datetime.today().strftime('%Y%m%d%H%M%S'))
        self.content_mime_type = 'text/markdown'
        self.versification_slug = 'ufw'
        self.language = {'slug': 'en', 'name': 'English', 'dir': 'ltr'}
        self.resource = {
            'slug': slug,
            'name': name,
            'type': 'book'
        }
        self.resource['status'] = {
            'translate_mode': 'all',
            'checking_entity': [],
            'checking_level': '1',
            'version': '4',
            'comments': '',
            'contributors': [],
            'pub_date': datetime.today().strftime('%Y-%m-%d'),
            'license': 'CC BY-SA',
            'checks_performed': [],
            'source_translations': []
        }
        self.chunk_status = []

    def __contains__(self, item):
        return item in self.__dict__

    def to_serializable(self):
        return_val = OrderedDict([
            ('package_version', self.package_version),
            ('modified_at', self.modified_at),
            ('content_mime_type', self.content_mime_type),
            ('versification_slug', self.versification_slug),
            ('language', self.language),
            ('resource', self.resource),
            ('chunk_status', self.chunk_status)
        ])

        return return_val


class ResourceManifestEncoder(JSONEncoder):
    def default(self, o):
        """
        :param OBSManifest o:
        :return:
        """
        return o.to_serializable()


def run_git(params, working_folder):
    results = run_git_full_response(params, working_folder)
    success = (results.returncode == 0)
    return success


def run_git_full_response(params, working_folder):
    print("Doing git {0}".format(params[0]))
    initial_dir = os.path.abspath(os.curdir)
    os.chdir(working_folder)
    command = ['git'] + params
    results = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.chdir(initial_dir)  # restore curdir
    if (results.returncode != 0):
        print("Git ERROR: " + results.stdout.decode("utf-8", "ignore") + results.stderr.decode("utf-8", "ignore"))
    return results


def is_git_changed(source_repo_name):
    response = run_git_full_response(['status', '--porcelain'], source_repo_name)
    changed = False
    untracked = False
    if response.stdout:
        lines = response.stdout.decode("utf-8", "ignore").split('\n')
        for line in lines:
            prefix = line.strip().split(' ')
            if prefix[0] == 'D':
                untracked = True
                changed = True
            elif prefix[0] == '??':
                untracked = True
                changed = True
            elif prefix[0] == 'M':
                changed = True
            elif prefix[0] == 'A':
                changed = True

            if changed and line:
                print("changed: " + line)

    return changed, untracked

def get_git_url(url, access_token):
    """
    :param str|unicode url: URL to open
    :return response
    """
    headers = {
        'Authorization': 'token ' + access_token
    }

    response = requests.get(url, headers=headers)
    return response


def post_git_url(url, data, access_token):
    """
    :param str|unicode url: URL to open
    :return tuple of file contents and header Link
    """
    headers = {
        'Authorization': 'token ' + access_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(url, data, headers=headers)
    return response

def isRepoPresent(host_name, user, repo, access_token):
    url = host_name + '/api/v1/repos/{0}/{1}'.format(user, repo)
    response = get_git_url(url, access_token)
    text = response.text
    if not text:
        return False
    results = json.loads(text)
    return results and (len(results) > 0)


def createRepoInOrganization(host_name, org, repo, access_token):
    """
    Note that user must be the same as the user for access_token
    :param user:
    :param repo:
    :return:
    """
    url = '{0}/api/v1/org/{1}/repos'.format(host_name, org)
    data = 'name={0}'.format(repo)
    response = post_git_url(url, data, access_token)
    text = response.text
    if text:
        results = json.loads(text)
        if results and 'full_name' in results:
            full_name = '{0}/{1}'.format(org, repo)
            return results['full_name'] == full_name
    return False


def createRepoForCurrentUser(host_name, user, repo, access_token):
    """
    :param repo:
    :return:
    """
    url = host_name + '/api/v1/user/repos'
    data = 'name={0}'.format(repo)
    response = post_git_url(url, data, access_token)
    text = response.text
    if text:
        results = json.loads(text)
        if results and 'full_name' in results:
            full_name = '{0}/{1}'.format(user, repo)
            return results['full_name'] == full_name
    return False
