from __future__ import print_function, unicode_literals

import codecs
import json
import os
import re
from general_tools.file_utils import write_file, make_dir
from general_tools.url_utils import get_languages, join_url_parts, get_url
from obs import chapters_and_frames
from obs.obs_classes import OBS, OBSManifest, OBSSourceTranslation, OBSManifestEncoder
from converters.common import quiet_print, dokuwiki_to_markdown


class OBSConverter(object):
    """
    Converts an obs translation from DokuWiki format to Resource Container format.
    """

    # regular expressions for removing text formatting
    html_tag_re = re.compile(r'<.*?>', re.UNICODE)
    link_tag_re = re.compile(r'\[\[.*?\]\]', re.UNICODE)

    book_title_re = re.compile(r'^\_\_([^\_]+)\_\_', re.UNICODE)
    chapter_title_re = re.compile(r'^#([^#]+)#', re.UNICODE)
    chapter_reference_re = re.compile(r'^\_([^\_]+)\_', re.UNICODE | re.MULTILINE)
    image_re = re.compile(r'^\!\[Image\]', re.UNICODE | re.MULTILINE)

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

        # remove trailing slash
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
            chapter_file = os.path.join(story_dir, file_to_download.replace('.txt', '.md'))
            self.download_obs_file(base_url, file_to_download, chapter_file)
            # split chapters into chunks
            chapter_slug = file_to_download.replace('.txt', '')
            self.chunk_chapter(chapter_file, os.path.join(story_dir, chapter_slug))
            os.remove(chapter_file)

        # download front and back matter
        self.download_obs_file(base_url, 'front-matter.txt', os.path.join(self.out_dir, 'content', 'front', 'intro.md'))
        self.download_obs_file(base_url, 'back-matter.txt', os.path.join(self.out_dir, 'content', 'back', 'intro.md'))

        # book title
        with codecs.open(os.path.join(self.out_dir, 'content', 'front', 'intro.md'), 'r', encoding='utf-8') as in_front_file:
            front_data = in_front_file.read()
            if self.book_title_re.search(front_data):
                title = self.book_title_re.search(front_data).group(1)
                write_file(os.path.join(self.out_dir, 'content', 'front', 'title.md'), title)

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

    def chunk_chapter(self, chapter_file, chapter_dir):
        make_dir(chapter_dir)
        with codecs.open(chapter_file, 'r', encoding='utf-8') as in_file:
            data = in_file.read()

            # title
            if self.chapter_title_re.search(data):
                title = self.chapter_title_re.search(data).group(1)
                write_file(os.path.join(chapter_dir, 'title.md'), title)
                data = self.chapter_title_re.sub('', data).lstrip()

            # reference
            if self.chapter_reference_re.search(data):
                reference = self.chapter_reference_re.search(data).group(1)
                write_file(os.path.join(chapter_dir, 'reference.md'), reference)
                data = self.chapter_reference_re.sub('', data).rstrip()

            # chunks
            chunks = self.image_re.split(data)
            chunk_num = 1
            for chunk in chunks:
                out_file = os.path.join(chapter_dir, str(chunk_num).zfill(2)) + '.md'
                write_file(out_file, '![Image]'+chunk)
                chunk_num += 1

    def download_obs_file(self, base_url, file_to_download, out_file):

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

        save_as = out_file

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
