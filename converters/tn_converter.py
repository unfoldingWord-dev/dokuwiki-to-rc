from __future__ import print_function, unicode_literals
import json
import os
import re
from general_tools.file_utils import write_file
from general_tools.url_utils import get_languages, join_url_parts, get_url
from converters.common import quiet_print, dokuwiki_to_markdown, NewResourceManifest, ResourceManifestEncoder


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

    def __init__(self, lang_code, git_repo, out_dir, quiet, overwrite):
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
        quiet_print(self.quiet, 'Downloading language data...', end=' ')
        langs = get_languages()
        quiet_print(self.quiet, 'finished.')

        self.lang_data = next((l for l in langs if l['lc'] == lang_code), '')

        if not self.lang_data:
            raise Exception('Information for language "{0}" was not found.'.format(lang_code))

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

        quiet_print(self.quiet, 'Getting OBS frame URLs...', end=' ')
        frames_list = [o['download_url'] for o in json.loads(get_url(frames_api_url))]
        quiet_print(self.quiet, 'finished.')

        target_dir = os.path.join(self.out_dir, 'content')
        for url in frames_list:
            if url:
                self.download_frame_file(url, target_dir)

        # get the status
        uwadmin_dir = 'https://raw.githubusercontent.com/Door43/d43-en/master/uwadmin'
        status = self.get_json_dict(join_url_parts(uwadmin_dir, lang_code, 'obs/status.txt'))
        manifest = NewResourceManifest('obs-tn', 'OBS translationNotes')
        manifest.resource['status']['pub_date'] = status['publish_date']
        manifest.resource['status']['contributors'] = re.split(r'\s*;\s*|\s*,\s*', status['contributors'])
        manifest.resource['status']['checking_level'] = status['checking_level']
        manifest.resource['status']['comments'] = status['comments']
        manifest.resource['status']['version'] = status['version']
        manifest.resource['status']['checking_entity'] = re.split(r'\s*;\s*|\s*,\s*', status['checking_entity'])

        manifest.resource['status']['source_translations'].append({
            'language_slug': status['source_text'],
            'resource_slug': 'obs',
            'version': status['source_text_version']
        })

        manifest.language['slug'] = lang_code
        manifest.language['name'] = self.lang_data['ang']
        manifest.language['dir'] = self.lang_data['ld']

        manifest_str = json.dumps(manifest, sort_keys=False, indent=2, cls=ResourceManifestEncoder)
        write_file(os.path.join(self.out_dir, 'package.json'), manifest_str)

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

    def get_json_dict(self, download_url):
        return_val = {}
        status_text = get_url(download_url)
        status_text = status_text.replace('\r', '')
        lines = filter(bool, status_text.split('\n'))

        for line in lines:

            if line.startswith('#') or line.startswith('\n') or line.startswith('{{') or ':' not in line:
                continue

            newline = self.clean_text(line)
            k, v = newline.split(':', 1)
            return_val[k.strip().lower().replace(' ', '_')] = v.strip()

        return return_val
