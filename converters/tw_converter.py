from __future__ import print_function, unicode_literals
import json
import os
import re
from general_tools.file_utils import write_file
from general_tools.url_utils import get_languages, join_url_parts, get_url
from converters.common import quiet_print, dokuwiki_to_markdown, ResourceManifest, ResourceManifestEncoder, post_url


class TWConverter(object):

    # [[:en:obe:kt:adultery|adultery, adulterous, adulterer, adulteress]]
    tw_link_re = re.compile(r'\[\[.*?:obe:(kt|other):(.*?)\]\]', re.UNICODE)
    obs_link_re = re.compile(r'\[\[.*?:obs:notes:frames:(.*?)\]{2,3}', re.UNICODE)
    squiggly_re = re.compile(r'~~(?:DISCUSSION|NOCACHE)~~', re.UNICODE)
    extra_blanks_re = re.compile(r'\n{3,}', re.UNICODE)
    page_query_re = re.compile(r'\{\{door43pages.*@:?(.*?)\s.*-q="(.*?)".*\}\}', re.UNICODE)
    tag_re = re.compile(r'\{\{tag>.*?\}\}', re.UNICODE)
    langs = None

    def __init__(self, lang_code, git_repo, out_dir, quiet, flat_format=False):
        """

        :param unicode lang_code:
        :param unicode git_repo:
        :param unicode out_dir:
        :param bool quiet:
        """
        self.git_repo = git_repo
        self.out_dir = out_dir
        self.quiet = quiet
        # self.temp_dir = tempfile.mkdtemp()

        if 'github' not in git_repo:
            raise Exception('Currently only github repositories are supported.')

        # get the language data
        if TWConverter.langs:  # check if cached
            langs = TWConverter.langs
        else:
            try:
                quiet_print(self.quiet, 'Downloading language data...', end=' ')
                langs = get_languages()
                TWConverter.langs = langs
            finally:
                quiet_print(self.quiet, 'finished.')

        self.lang_data = next((l for l in langs if l['lc'] == lang_code), '')

        if not self.lang_data:
            raise Exception('Information for language "{0}" was not found.'.format(lang_code))

        self.flat_format = flat_format
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
        kt_api_url = join_url_parts(base_url, 'contents/obe/kt')
        other_api_url = join_url_parts(base_url, 'contents/obe/other')

        self.trying = 'Downloading kt file names'
        quiet_print(self.quiet, 'Downloading kt file names...', end=' ')
        kt_list = [o['download_url'] for o in json.loads(get_url(kt_api_url))]
        quiet_print(self.quiet, 'finished.')

        self.trying = 'Downloading other file names'
        quiet_print(self.quiet, 'Downloading other file names...', end=' ')
        other_list = [o['download_url'] for o in json.loads(get_url(other_api_url))]
        quiet_print(self.quiet, 'finished.')

        self.trying = 'Downloading kt files'
        target_dir = os.path.join(self.out_dir, 'content', 'kt')
        for url in kt_list:
            self.download_tw_file(url, target_dir)

        self.trying = 'Downloading other files'
        target_dir = os.path.join(self.out_dir, 'content', 'other')
        for url in other_list:
            self.download_tw_file(url, target_dir)

        self.trying = 'Saving Manifest'
        manifest = ResourceManifest('tw', 'translationWords')
        manifest.status['checking_level'] = '3'
        manifest.status['version'] = '3'
        manifest.status['checking_entity'] = 'Wycliffe Associates'

        manifest.language['slug'] = lang_code
        manifest.language['name'] = self.lang_data['ang']
        manifest.language['dir'] = self.lang_data['ld']

        manifest_str = json.dumps(manifest, sort_keys=False, indent=2, cls=ResourceManifestEncoder)
        write_file(os.path.join(self.out_dir, 'manifest.json'), manifest_str)

    def download_tw_file(self, url_to_download, out_dir):

        file_name = url_to_download.rsplit('/', 1)[1]
        save_as = os.path.join(out_dir, file_name.replace('.txt', '.md'))
        if os.path.isfile(save_as):
            quiet_print(self.quiet, 'Skipping {0}.'.format(file_name))
            return

        try:
            quiet_print(self.quiet, 'Downloading {0}...'.format(url_to_download), end=' ')
            dw_text = get_url(url_to_download)

        finally:
            quiet_print(self.quiet, 'finished.')

        quiet_print(self.quiet, 'Converting {0} to markdown...'.format(file_name), end=' ')
        md_text = dokuwiki_to_markdown(dw_text)

        # old_url = 'https://api.unfoldingword.org/obs/jpg/1/en/'
        # cdn_url = 'https://cdn.door43.org/obs/jpg/'
        # md_text = md_text.replace(old_url, cdn_url)

        # fix links to other tW articles
        md_text = self.update_tw_links(md_text)  # self.tw_link_re.sub(r'[\3](../\1/\2.md)', md_text)
        md_text = self.update_obs_links(md_text)

        # remove tags
        md_text = self.tag_re.sub(r'', md_text)

        # remove squiggly tags
        md_text = self.squiggly_re.sub(r'', md_text)

        # get page query
        md_text = self.get_page_query(md_text)

        # remove extra blank lines
        md_text = self.extra_blanks_re.sub(r'\n\n', md_text)

        quiet_print(self.quiet, 'finished.')

        quiet_print(self.quiet, 'Saving {0}...'.format(save_as), end=' ')
        write_file(save_as, md_text)
        quiet_print(self.quiet, 'finished.')

    def get_page_query(self, md_text):

        search_results = self.page_query_re.search(md_text)
        if not search_results:
            return md_text

        post_data = {'call': 'get_door43pagequery2',
                     'data[subns]': 'false',
                     'data[nopages]': 'false',
                     'data[simpleList]': 'false',
                     'data[lineBreak]': 'true',
                     'data[excludedPages][]': 'home',
                     'data[title]': 'true',
                     'data[wantedNS]': '',
                     'data[wantedDir]': '',
                     'data[safe]': 'true',
                     'data[textNS]': '',
                     'data[textPages]': '',
                     'data[maxDepth]': '0',
                     'data[nbCol]': '3',
                     'data[simpleLine]': 'false',
                     'data[sortid]': 'false',
                     'data[reverse]': 'false',
                     'data[pagesinns]': 'false',
                     'data[anchorName]': '',
                     'data[actualTitleLevel]': 'false',
                     'data[idAndTitle]': 'false',
                     'data[nbItemsMax]': '0',
                     'data[numberedList]': 'false',
                     'data[natOrder]': 'false',
                     'data[sortDate]': 'false',
                     'data[useLegacySyntax]': 'false',
                     'data[hidenopages]': 'false',
                     'data[hidenosubns]': 'false',
                     'data[requested_namespaces][]': search_results.group(1),
                     'data[requested_directories][]': search_results.group(1).replace(':', '/'),
                     'data[showcount]': 'false',
                     'data[fontsize][]': '100%',
                     'data[pos]': '1638',
                     'data[query][]': search_results.group(2),
                     'data[div_id]': '66D43DB7-68D9-781D-F94B-37FCAAAC0171'
                     }

        response = json.loads(post_url('https://door43.org/lib/exe/ajax.php', post_data))
        listing = '\n'

        for ref in response:
            listing += '* [{0}](https://door43.org{1})\n'.format(ref[1], ref[0])

        md_text = self.page_query_re.sub(listing, md_text)

        return md_text

    def update_tw_links(self, md_text):

        search_results = self.tw_link_re.search(md_text)
        if not search_results:
            return md_text

        return self.tw_link_re.sub(self.replace_tw_link, md_text)

    @staticmethod
    def replace_tw_link(match):

        parts = match.group(2).split('|', 1)

        if len(parts) == 1:
            return '[{0}](../{1}/{0}.md)'.format(parts[0], match.group(1))

        return '[{0}](../{1}/{2}.md)'.format(parts[1], match.group(1), parts[0])

    def update_obs_links(self, md_text):

        search_results = self.obs_link_re.search(md_text)
        if not search_results:
            return md_text

        return self.obs_link_re.sub(self.replace_obs_link, md_text)

    @staticmethod
    def replace_obs_link(match):

        parts = match.group(1).split('|', 1)
        return '[{0}](https://door43.org/en/obs/notes/frames/{0})'.format(parts[0])

    def not_translated(self):
        return False  # stub out for now
