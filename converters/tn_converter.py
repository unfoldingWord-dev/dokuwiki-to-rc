from __future__ import print_function, unicode_literals
import json
import os
import re
import shutil
from datetime import datetime
from general_tools import file_utils
from general_tools.file_utils import write_file
from general_tools.url_utils import get_languages, join_url_parts, get_url
from resource_container import factory
from converters.common import quiet_print, dokuwiki_to_markdown, NewResourceManifest, ResourceManifestEncoder
from converters.unicode_utils import to_str


class TNConverter(object):

    # [[:en:obe:kt:adultery|adultery, adulterous, adulterer, adulteress]]
    tw_link_re = re.compile(r'\[\[.*?:obe:(kt|other):(.+?)\]\]', re.UNICODE)
    nav_links_re = re.compile(r'__\[\[.*:obs:notes:.*(<<|Up|>>).*\]\]__', re.UNICODE)
    squiggly_re = re.compile(r'~~(?:DISCUSSION|NOCACHE)~~', re.UNICODE)
    extra_blanks_re = re.compile(r'\n{3,}', re.UNICODE)
    page_query_re = re.compile(r'\{\{door43pages.*@:?(.*?)\s.*-q="(.*?)".*\}\}', re.UNICODE)
    tag_re = re.compile(r'\{\{tag>.*?\}\}', re.UNICODE)
    html_tag_re = re.compile(r'<.*?>', re.UNICODE)
    link_tag_re = re.compile(r'\[\[.*?\]\]', re.UNICODE)
    langs = None

    def __init__(self, lang_code, git_repo, out_dir, quiet, overwrite, ignore_lang_code_error=False):
        """

        :param unicode lang_code:
        :param unicode git_repo:
        :param unicode out_dir:
        :param bool quiet:
        :param bool overwrite:
        """
        self.git_repo = git_repo
        self.out_dir = out_dir
        self.quiet = quiet
        self.overwrite = overwrite
        # self.temp_dir = tempfile.mkdtemp()

        if 'github' not in git_repo and 'file://' not in git_repo:
            raise Exception('Currently only github repositories are supported.')

        # get the language data
        if TNConverter.langs:  # check if cached
            langs = TNConverter.langs
        else:
            try:
                quiet_print(self.quiet, 'Downloading language data...', end=' ')
                langs = get_languages()
                TNConverter.langs = langs
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
        lang_code = self.lang_data['lc']

        # clean up the git repo url
        if self.git_repo[-4:] == '.git':
            self.git_repo = self.git_repo[:-4]

        if self.git_repo[-1:] == '/':
            self.git_repo = self.git_repo[:-1]

        # get the source files from the git repository
        base_url = self.git_repo.replace('github.com', 'api.github.com/repos')
        frames_api_url = join_url_parts(base_url, 'contents/obs/notes/frames')

        self.trying = 'Getting OBS frame URLs'
        quiet_print(self.quiet, 'Getting OBS frame URLs...', end=' ')
        frames_list = [o['download_url'] for o in json.loads(get_url(frames_api_url))]
        quiet_print(self.quiet, 'finished.')

        self.trying = 'Downloads OBS frame files'
        target_dir = os.path.join(self.out_dir, 'content')
        for url in frames_list:
            if url:
                self.download_frame_file(url, target_dir)

        status = self.get_uw_status(lang_code)

        self.trying = 'creating manifest'
        title = 'OBS translationNotes'
        manifest = {
            'dublin_core': {
                'title': title,
                'type': 'help',
                'format': 'text/markdown',
                'contributor': [
                    'Door43 World Missions Community'
                ],
                'creator': 'Door43 World Missions Community',
                'description': 'Open-licensed exegetical notes that provide historical, cultural, and linguistic information for translators. It provides translators and checkers with pertinent, just-in-time information to help them make the best possible translation decisions.',
                'identifier': 'obs-tn',
                'language': {
                    'direction': self.lang_data['ld'],
                    'identifier': status['source_text'],
                    'title': self.lang_data['ang']
                },
                'modified': datetime.today().strftime('%Y-%m-%d'),
                'publisher': 'unfoldingWord',
                'relation': [
                    'en/obs'
                ],
                'source': [{
                    'identifier': 'obs-tn',
                    'language': status['source_text'],
                    'version': status['source_text_version']
                }],
                'subject': 'Translator Notes',
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
        rc_folder = os.path.join(self.out_dir, 'rc')
        shutil.rmtree(rc_folder, ignore_errors=True)
        rc = factory.create(rc_folder, manifest)
        shutil.move(os.path.join(rc_folder, 'manifest.yaml'), self.out_dir)
        shutil.rmtree(rc_folder, ignore_errors=True)

    def download_frame_file(self, url_to_download, out_dir):
        dw_filename = url_to_download.rsplit('/', 1)[1]

        if not dw_filename.endswith('.txt'):
            quiet_print(self.quiet, 'Skipping non-dokuwiki file {0}.'.format(dw_filename))
            return

        chapter_dir = dw_filename.split('-')[0]
        md_filename = dw_filename.split('-')[1].replace('.txt', '.md')
        save_as = os.path.join(out_dir, chapter_dir, md_filename)
        if not self.overwrite and os.path.isfile(save_as):
            quiet_print(self.quiet, 'Skipping {0}.'.format(dw_filename))
            return

        # for test cases
        if self.git_repo.startswith('file://'):
            url_to_download = os.path.join(self.git_repo, 'master', 'obs', 'notes', 'frames', dw_filename)

        try:
            quiet_print(self.quiet, 'Downloading {0}...'.format(url_to_download), end=' ')
            text = get_url(url_to_download)
        finally:
            quiet_print(self.quiet, 'finished.')

        quiet_print(self.quiet, 'Converting {0} to markdown...'.format(dw_filename), end=' ')

        text = dokuwiki_to_markdown(text)
        text = self.update_tw_links(text)
        text = self.remove_nav_links(text)

        # # remove tags
        # text = self.tag_re.sub(r'', text)
        #
        # # remove squiggly tags
        # text = self.squiggly_re.sub(r'', text)
        #
        # # remove extra blank lines
        # text = self.extra_blanks_re.sub(r'\n\n', text)

        quiet_print(self.quiet, 'finished.')

        quiet_print(self.quiet, 'Saving {0}...'.format(save_as), end=' ')
        write_file(save_as, text)
        quiet_print(self.quiet, 'finished.')

    def update_tw_links(self, text):
        search_results = self.tw_link_re.search(text)
        if not search_results:
            return text
        else:
            return self.tw_link_re.sub(self.replace_tw_link, text)

    def replace_tw_link(self, match):
        parts = match.group(2).split('|', 1)
        if len(parts) == 1:
            return '[{0}](https://git.door43.org/Door43/en-tw/src/master/content/{1}/{0}.md)'.format(parts[0], match.group(1))
        else:
            return '[{0}](https://git.door43.org/Door43/en-tw/src/master/content/{1}/{2}.md)'.format(parts[1], match.group(1), parts[0])

    def remove_nav_links(self, text):
        return self.nav_links_re.sub(r'', text)

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
