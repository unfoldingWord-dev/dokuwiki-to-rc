from __future__ import print_function, unicode_literals
import json
import os
import re
from general_tools.file_utils import write_file
from general_tools.url_utils import get_languages, join_url_parts, get_url
from obs.obs_classes import OBS, OBSManifest, OBSSourceTranslation, OBSManifestEncoder
from converters.common import quiet_print, dokuwiki_to_markdown


class OBSConverter(object):

    # regular expressions for removing text formatting
    html_tag_re = re.compile(r'<.*?>', re.UNICODE)
    link_tag_re = re.compile(r'\[\[.*?\]\]', re.UNICODE)

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
        # self.temp_dir = ''

        if 'github' not in git_repo and 'file://' not in git_repo:
            raise Exception('Currently only github repositories are supported.')

        # get the language data
        try:
            quiet_print(self.quiet, 'Downloading language data...', end=' ')
            langs = get_languages()
        finally:
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

        # pre-flight checklist
        if self.git_repo[-1:] == '/':
            self.git_repo = self.git_repo[:-1]

        # get the source files from the git repository
        base_url = self.git_repo.replace('github.com', 'raw.githubusercontent.com')

        # initialize
        obs_obj = OBS()
        obs_obj.direction = self.lang_data['ld']
        obs_obj.language = lang_code

        # download needed files from the repository
        files_to_download = []
        for i in range(1, 51):
            files_to_download.append(str(i).zfill(2) + '.txt')

        # download OBS story files
        story_dir = os.path.join(self.out_dir, 'content')
        for file_to_download in files_to_download:
            self.download_obs_file(base_url, file_to_download, story_dir)

        # download front and back matter
        self.download_obs_file(base_url, 'front-matter.txt', os.path.join(self.out_dir, 'content', '_front'))
        self.download_obs_file(base_url, 'back-matter.txt', os.path.join(self.out_dir, 'content', '_back'))

        # get the status
        uwadmin_dir = 'https://raw.githubusercontent.com/Door43/d43-en/master/uwadmin'
        status = self.get_json_dict(join_url_parts(uwadmin_dir, lang_code, 'obs/status.txt'))
        manifest = OBSManifest()
        manifest.package_version = 0.1
        manifest.resource['status']['pub_date'] = status['publish_date']
        manifest.resource['status']['contributors'] = re.split(r'\s*;\s*|\s*,\s*', status['contributors'])
        manifest.resource['status']['checking_level'] = status['checking_level']
        manifest.resource['status']['comments'] = status['comments']
        manifest.resource['status']['version'] = status['version']
        manifest.resource['status']['checking_entity'] = re.split(r'\s*;\s*|\s*,\s*', status['checking_entity'])

        source_translation = OBSSourceTranslation()
        source_translation.language_slug = status['source_text']
        source_translation.resource_slug = 'obs'
        source_translation.version = status['source_text_version']

        manifest.resource['status']['source_translations'].append(source_translation)

        manifest.language['slug'] = lang_code
        manifest.language['name'] = self.lang_data['ang']
        manifest.language['dir'] = self.lang_data['ld']

        manifest_str = json.dumps(manifest, sort_keys=False, indent=2, cls=OBSManifestEncoder)
        write_file(os.path.join(self.out_dir, 'package.json'), manifest_str)

    def download_obs_file(self, base_url, file_to_download, out_dir):

        download_url = join_url_parts(base_url, 'master/obs', file_to_download)

        try:
            quiet_print(self.quiet, 'Downloading {0}...'.format(download_url), end=' ')
            dw_text = get_url(download_url)  # .decode('utf-8')

        finally:
            quiet_print(self.quiet, 'finished.')

        quiet_print(self.quiet, 'Converting {0} to markdown...'.format(file_to_download), end=' ')
        md_text = dokuwiki_to_markdown(dw_text)

        old_url = 'https://api.unfoldingword.org/obs/jpg/1/en/'
        cdn_url = 'https://cdn.door43.org/obs/jpg/'
        md_text = md_text.replace(old_url, cdn_url)

        quiet_print(self.quiet, 'finished.')

        save_as = os.path.join(out_dir, file_to_download.replace('.txt', '.md'))

        quiet_print(self.quiet, 'Saving {0}...'.format(save_as), end=' ')
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
