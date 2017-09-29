from __future__ import print_function, unicode_literals

import codecs
import inspect
import json
import os
import re
import shutil
from datetime import datetime
from general_tools import file_utils
from general_tools.file_utils import write_file
from general_tools.url_utils import get_languages, join_url_parts, get_url
from resource_container import factory
from converters.common import quiet_print, dokuwiki_to_markdown, ResourceManifest, ResourceManifestEncoder
from converters.unicode_utils import to_str


class TQConverter(object):

    tag_re = re.compile(r'\{\{tag>.*?\}\}', re.UNICODE)
    squiggly_re = re.compile(r'~~(?:DISCUSSION|NOCACHE)~~', re.UNICODE)
    extra_blanks_re = re.compile(r'\n{3,}', re.UNICODE)
    chapter_link_re = re.compile(r'\[\[:en:bible:questions:comprehension:(.*?):home\|(.*?)\]\]', re.UNICODE)
    missing_blank_line_re = re.compile(r'(\n    \*.*\n)(__)', re.UNICODE)
    story_num_re = re.compile(r'(Story )#', re.UNICODE)
    navigate_re = re.compile(r'\[\[:en:obs:notes:questions:(.*?)\|\s*(.*?)\s*\]\]', re.UNICODE)
    navigate2_re = re.compile(r'\[\[en/obs/notes/questions/(.*?)\|\s*(.*?)\s*\]\]', re.UNICODE)
    html_tag_re = re.compile(r'<.*?>', re.UNICODE)
    link_tag_re = re.compile(r'\[\[.*?\]\]', re.UNICODE)
    langs = None

    def __init__(self, lang_code, git_repo, bible_out_dir, obs_out_dir, quiet, ignore_lang_code_error=False):
        """

        :param str|unicode lang_code:
        :param str|unicode git_repo:
        :param str|unicode bible_out_dir:
        :param str|unicode obs_out_dir:
        :param bool quiet:
        """
        self.git_repo = git_repo
        self.bible_out_dir = bible_out_dir
        self.obs_out_dir = obs_out_dir
        self.quiet = quiet
        # self.temp_dir = tempfile.mkdtemp()

        if 'github' not in git_repo:
            raise Exception('Currently only github repositories are supported.')

        # get the language data
        if TQConverter.langs:  # check if cached
            langs = TQConverter.langs
        else:
            try:
                quiet_print(self.quiet, 'Downloading language data...', end=' ')
                langs = get_languages()
                TQConverter.langs = langs
            finally:
                quiet_print(self.quiet, 'finished.')

        self.lang_data = next((l for l in langs if l['lc'] == lang_code), '')

        if not self.lang_data:
            if ignore_lang_code_error:
                self.lang_data = {  # default language data
                    'lc': lang_code,
                    'direction': '',
                    'title': lang_code
                }
            else:
                raise Exception('Information for language "{0}" was not found.'.format(lang_code))

        # read the github access token
        root_dir = os.path.dirname(os.path.dirname(inspect.stack()[0][1]))
        with codecs.open(os.path.join(root_dir, 'github_api_token'), 'r', 'utf-8-sig') as in_file:
            # read the text from the file
            self.access_token = in_file.read()

        self.trying = 'Init'
        self.english = lang_code[:2] == 'en'
        self.translated_titles = 0

    def __enter__(self):
        return self

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        # delete temp files
        # if os.path.isdir(self.temp_dir):
        #     shutil.rmtree(self.temp_dir, ignore_errors=True)
        pass

    def run(self):

        # https://          github.com/Door43/d43-en
        # https://api.github.com/repos/door43/d43-en/contents/obe/kt
        # https://api.github.com/repos/door43/d43-en/contents/obe/other
        lang_code = self.lang_data['lc']

        # clean up the git repo url
        if self.git_repo[-4:] == '.git':
            self.git_repo = self.git_repo[:-4]

        if self.git_repo[-1:] == '/':
            self.git_repo = self.git_repo[:-1]

        # get the source files from the git repository
        base_url = self.git_repo.replace('github.com', 'api.github.com/repos')
        bible_api_url = join_url_parts(base_url, 'contents/bible/questions/comprehension')
        obs_api_url = join_url_parts(base_url, 'contents/obs/notes/questions')

        status = self.get_uw_status(lang_code)

        if self.bible_out_dir:
            self.trying = 'Downloading Bible tQ list'
            quiet_print(self.quiet, 'Downloading Bible tQ list.')
            bible_list = self.process_api_request(bible_api_url)
            quiet_print(self.quiet, 'Finished downloading Bible tQ list.')

            self.trying = 'Downloading Bible content'
            target_dir = os.path.join(self.bible_out_dir, 'content')
            for url in bible_list:
                self.download_bible_file(url, target_dir)

            manifest = ResourceManifest('tq', 'translationQuestions')
            manifest.status['checking_level'] = '3'
            manifest.status['version'] = '3'
            manifest.status['checking_entity'] = 'Wycliffe Associates'

            manifest.language['slug'] = lang_code
            manifest.language['name'] = self.lang_data['ang']
            manifest.language['dir'] = self.lang_data['ld']

            manifest_str = json.dumps(manifest, sort_keys=False, indent=2, cls=ResourceManifestEncoder)
            write_file(os.path.join(self.bible_out_dir, 'manifest.json'), manifest_str)

        if self.obs_out_dir:
            self.trying = 'Downloading OBS tQ list'
            quiet_print(self.quiet, 'Downloading OBS tQ list.')
            obs_list = self.process_api_request(obs_api_url)
            quiet_print(self.quiet, 'Finished downloading OBS tQ list.')

            self.trying = 'Downloading OBS content'
            target_dir = os.path.join(self.obs_out_dir, 'content')
            for url in obs_list:
                self.download_obs_file(url, target_dir)

            title = 'OBS translationQuestions'
            manifest = {
                'dublin_core': {
                    'title': title,
                    'type': 'help',
                    'format': 'text/markdown',
                    'contributor': [
                        'Door43 World Missions Community'
                    ],
                    'creator': 'Door43 World Missions Community',
                    'description': 'Comprehension and theological questions for Open Bible Stories. It enables translators and translation checkers to confirm that the intended meaning of their translations is clearly communicated to the speakers of that language.',
                    'identifier': 'obs-tq',
                    'language': {
                        'direction': self.lang_data['ld'],
                        'identifier': self.lang_data['lc'],
                        'title': self.lang_data['ang']
                    },
                    'modified': datetime.today().strftime('%Y-%m-%d'),
                    'publisher': 'unfoldingWord',
                    'relation': [
                        'en/obs'
                    ],
                    'source': [{
                        'identifier': 'obs-tq',
                        'language': status['source_text'],
                        'version': status['source_text_version']
                    }],
                    'subject': 'Translator Questions',
                    'version': status['version'],
                    'issued': status['publish_date'],
                    'rights': 'CC BY-SA 4.0'
                },
                'checking': {
                    'checking_entity': re.split(r'\s*;\s*|\s*,\s*', status['checking_entity']),
                    'checking_level': status['checking_level']
                },
                'projects': [{
                    'categories': [],
                    'identifier': 'obs',
                    'path': './content',
                    'sort': 0,
                    'title': title,
                    'versification': '"ufw"'
                }]
            }

            manifest = to_str(manifest)
            rc_folder = os.path.join(self.obs_out_dir, 'rc')
            shutil.rmtree(rc_folder, ignore_errors=True)
            rc = factory.create(rc_folder, manifest)
            shutil.move(os.path.join(rc_folder, 'manifest.yaml'), self.obs_out_dir)
            shutil.rmtree(rc_folder, ignore_errors=True)

    def process_api_request(self, url):

        quiet_print(self.quiet, '   Getting {0}.'.format(url))

        if '?' in url:
            url += '&access_token={0}'.format(self.access_token)
        else:
            url += '?access_token={0}'.format(self.access_token)

        # get the directory listing
        items = json.loads(get_url(url))

        # collect the files
        file_list = [o['download_url'] for o in items if o['type'] == 'file'
                     and o['name'] != 'home.txt'
                     and o['name'] != 'sidebar.txt']

        # check for sub-directories
        dir_list = [o['url'] for o in items if o['type'] == 'dir']

        for sub_dir in dir_list:
            file_list.extend(self.process_api_request(sub_dir))

        return file_list

    def download_bible_file(self, url_to_download, out_dir):

        parts = url_to_download.rsplit('/', 2)
        file_name = parts[2]
        dir_name = parts[1]
        save_as = os.path.join(out_dir, dir_name, file_name.replace('.txt', '.md'))
        if os.path.isfile(save_as):
            quiet_print(self.quiet, 'Skipping {0}.'.format(file_name))
            return

        quiet_print(self.quiet, 'Downloading {0}...'.format(url_to_download), end=' ')
        dw_text = get_url(url_to_download)

        md_text = dokuwiki_to_markdown(dw_text)

        # fix links to chapter list
        # **[[:en:bible:questions:comprehension:1ch:home|Back to 1 Chronicles Chapter List]]**
        md_text = self.chapter_link_re.sub(r'[\2](./)', md_text)

        # remove tags
        md_text = self.tag_re.sub(r'', md_text)

        # remove squiggly tags
        md_text = self.squiggly_re.sub(r'', md_text)

        # remove extra blank lines
        md_text = self.extra_blanks_re.sub(r'\n\n', md_text)

        write_file(save_as, md_text)
        quiet_print(self.quiet, 'finished.')

    def download_obs_file(self, url_to_download, out_dir):

        parts = url_to_download.rsplit('/', 1)
        file_name = parts[1]
        save_as = os.path.join(out_dir, file_name.replace('.txt', '.md'))
        if os.path.isfile(save_as):
            quiet_print(self.quiet, 'Skipping {0}.'.format(file_name))
            return

        quiet_print(self.quiet, 'Downloading {0}...'.format(url_to_download), end=' ')
        dw_text = get_url(url_to_download)

        md_text = dokuwiki_to_markdown(dw_text)

        # fix links to chapter list
        # **[[:en:bible:questions:comprehension:1ch:home|Back to 1 Chronicles Chapter List]]**
        md_text = self.chapter_link_re.sub(r'[\2](./)', md_text)

        # remove tags
        md_text = self.tag_re.sub(r'', md_text)

        # remove squiggly tags
        md_text = self.squiggly_re.sub(r'', md_text)

        # remove extra blank lines
        md_text = self.extra_blanks_re.sub(r'\n\n', md_text)

        # insert missing blank line
        md_text = self.missing_blank_line_re.sub(r'\1\n\2', md_text)

        # fix story number
        md_text = self.story_num_re.sub(r'\1', md_text)

        # navigation
        md_text = self.navigate_re.sub(r'[\2](./\1.md)', md_text)
        md_text = self.navigate2_re.sub(r'[\2](./\1.md)', md_text)

        write_file(save_as, md_text)
        quiet_print(self.quiet, 'finished.')

    def clean_text(self, text):
        """
        Cleans up text from possible DokuWiki and HTML tag pollution.
        """
        if self.html_tag_re.search(text):
            text = self.html_tag_re.sub('', text)
        if self.link_tag_re.search(text):
            text = self.link_tag_re.sub('', text)
        return text

    def get_json_dict_from_url(self, download_url):
        status_text = get_url(download_url)
        return self.parse_data_file(status_text)

    def get_json_dict_from_file(self, file_path):
        status_text = file_utils.read_file(file_path)
        return self.parse_data_file(status_text)

    def parse_data_file(self, status_text):
        return_val = {}
        status_text = status_text.replace('\r', '')
        lines = filter(bool, status_text.split('\n'))
        for line in lines:

            if line.startswith('#') or line.startswith('\n') or line.startswith('{{') or ':' not in line:
                continue

            newline = self.clean_text(line)
            k, v = newline.split(':', 1)
            return_val[k.strip().lower().replace(' ', '_')] = v.strip()
        return return_val

    def get_uw_status(self, lang_code):
        uwadmin_dir = 'https://raw.githubusercontent.com/Door43/d43-en/master/uwadmin'
        status_path = join_url_parts(uwadmin_dir, lang_code, 'obs/status.txt')
        self.trying = 'getting UW status (' + status_path + ')'
        try:
            status = self.get_json_dict_from_url(status_path)
        except:
            print("UW Status not found, using defaults")
            status = self.get_json_dict_from_file('default_uw_status.txt')
        return status
