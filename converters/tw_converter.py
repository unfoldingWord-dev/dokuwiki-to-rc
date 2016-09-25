from __future__ import print_function, unicode_literals
import json
import os
from general_tools.file_utils import write_file
from general_tools.url_utils import get_languages, join_url_parts, get_url
from converters.common import quiet_print, dokuwiki_to_markdown, ResourceManifest, ResourceManifestEncoder


class TWConverter(object):

    def __init__(self, lang_code, git_repo, out_dir, quiet):
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

        quiet_print(self.quiet, 'Downloading kt file names...', end=' ')
        kt_list = [o['download_url'] for o in json.loads(get_url(kt_api_url))]
        quiet_print(self.quiet, 'finished.')

        quiet_print(self.quiet, 'Downloading other file names...', end=' ')
        other_list = [o['download_url'] for o in json.loads(get_url(other_api_url))]
        quiet_print(self.quiet, 'finished.')

        target_dir = os.path.join(self.out_dir, 'content', 'kt')
        for url in kt_list:
            self.download_tw_file(url, target_dir)

        target_dir = os.path.join(self.out_dir, 'content', 'other')
        for url in other_list:
            self.download_tw_file(url, target_dir)

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

        try:
            quiet_print(self.quiet, 'Downloading {0}...'.format(url_to_download), end=' ')
            dw_text = get_url(url_to_download)

        finally:
            quiet_print(self.quiet, 'finished.')

        quiet_print(self.quiet, 'Converting {0} to markdown...'.format(file_name), end=' ')
        md_text = dokuwiki_to_markdown(dw_text)

        old_url = 'https://api.unfoldingword.org/obs/jpg/1/en/'
        cdn_url = 'https://cdn.door43.org/obs/jpg/'
        md_text = md_text.replace(old_url, cdn_url)

        quiet_print(self.quiet, 'finished.')

        save_as = os.path.join(out_dir, file_name.replace('.txt', '.md'))

        quiet_print(self.quiet, 'Saving {0}...'.format(save_as), end=' ')
        write_file(save_as, md_text)
        quiet_print(self.quiet, 'finished.')
