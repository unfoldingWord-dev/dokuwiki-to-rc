from __future__ import print_function, unicode_literals

import codecs
import os
import re
from general_tools.file_utils import write_file, make_dir
from general_tools.url_utils import get_languages, join_url_parts, get_url
from obs.obs_classes import OBS, OBSManifest, OBSSourceTranslation, OBSManifestEncoder
from converters.common import quiet_print, dokuwiki_to_markdown
from resource_container import factory
import tempfile
import shutil
from datetime import datetime
from .unicode_utils import to_str


class OBSConverter(object):
    """
    Converts an obs translation from DokuWiki format to Resource Container format.
    """

    # regular expressions for removing text formatting
    html_tag_re = re.compile(r'<.*?>', re.UNICODE)
    link_tag_re = re.compile(r'\[\[.*?\]\]', re.UNICODE)
    dir_link_re = re.compile(r'\?direct&', re.UNICODE)

    book_title_re = re.compile(r'^\_\_([^\_]+)\_\_', re.UNICODE)
    chapter_title_re = re.compile(r'^#\s*([^#]+)#*', re.UNICODE)
    chapter_reference_re = re.compile(r'^\_([^\_]+)\_', re.UNICODE | re.MULTILINE)
    image_re = re.compile(r'^\!\[', re.UNICODE | re.MULTILINE)

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
        self.download_dir = tempfile.mkdtemp(prefix='OBS_TEMP')

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

        # download front and back matter
        front_path = os.path.join(self.download_dir, 'content', 'front', 'intro.md')
        self.download_obs_file(base_url, 'front-matter.txt', front_path)
        back_path = os.path.join(self.download_dir, 'content', 'back', 'intro.md')
        self.download_obs_file(base_url, 'back-matter.txt', back_path)

        # book title
        with codecs.open(os.path.join(self.download_dir, 'content', 'front', 'intro.md'), 'r', encoding='utf-8') as in_front_file:
            front_data = in_front_file.read()
            if self.book_title_re.search(front_data):
                # TODO: split by pipe and just grab the last bit
                title = self.book_title_re.search(front_data).group(1)
                # clean piped titles
                title = title.split('|')[-1].lstrip().rstrip()

        # download needed files from the repository
        files_to_download = []
        for i in range(1, 51):
            files_to_download.append(str(i).zfill(2) + '.txt')

        # get the status
        uwadmin_dir = 'https://raw.githubusercontent.com/Door43/d43-en/master/uwadmin'
        status = self.get_json_dict(join_url_parts(uwadmin_dir, lang_code, 'obs/status.txt'))
        manifest = OBSManifest()
        manifest.resource['status']['comments'] = status['comments']

        new_manifest = {
            'dublin_core': {
                'title': title,
                'type': 'book',
                'format': manifest.content_mime_type,
                'contributor': re.split(r'\s*;\s*|\s*,\s*', status['contributors']),
                'identifier': manifest.resource['slug'],
                'language': {
                    'direction': self.lang_data['ld'],
                    'identifier': status['source_text'],
                    'title': self.lang_data['ang']
                },
                'modified': datetime.today().strftime('%Y-%m-%d'),
                'source': [{
                    'identifier': manifest.resource['slug'],
                    'language': manifest.language['slug'],
                    'version': status['source_text_version']
                }],
                'version': status['version'],
                'issued': status['publish_date'],
                'rights': 'CC BY-SA 4.0'
            },
            'checking': {
                'checking_entity': re.split(r'\s*;\s*|\s*,\s*', status['checking_entity']),
                'checking_level': status['checking_level']
            },
            'projects': [{
                'categories': None,
                'identifier': manifest.resource['slug'],
                'path': './content',
                'sort': 0,
                'title': title,
                'versification': manifest.versification_slug
            }]
        }
        shutil.rmtree(self.out_dir)

        new_manifest = to_str(new_manifest)

        rc = factory.create(self.out_dir, new_manifest)

        # download OBS story files
        story_dir = os.path.join(self.download_dir, 'content')
        for file_to_download in files_to_download:
            chapter_file = os.path.join(story_dir, file_to_download)
            self.download_obs_file(base_url, file_to_download, chapter_file)
            # split chapters into chunks
            chapter_slug = file_to_download.replace('.txt', '')
            self.chunk_chapter(rc, chapter_file, chapter_slug)
            os.remove(chapter_file)

        rc.write_chunk('front', 'title', title)
        rc.write_chunk('front', 'intro', codecs.open(front_path, 'r', encoding='utf-8').read())
        rc.write_chunk('back', 'intro', codecs.open(back_path, 'r', encoding='utf-8').read())
        dir_path = os.path.dirname(os.path.realpath(__file__))
        shutil.copy(os.path.join(dir_path, 'LICENSE.md'), os.path.join(self.out_dir, 'LICENSE.md'))

    def chunk_chapter(self, rc, chapter_file, chapter):
        with codecs.open(chapter_file, 'r', encoding='utf-8') as in_file:
            data = in_file.read()

            # title
            if self.chapter_title_re.search(data):
                title = self.chapter_title_re.search(data).group(1).rstrip()
                print('TITLE: ', title)
                rc.write_chunk(chapter, 'title', title)
                data = self.chapter_title_re.sub('', data).lstrip()

            # reference
            if self.chapter_reference_re.search(data):
                reference = self.chapter_reference_re.search(data).group(1)
                rc.write_chunk(chapter, 'reference', reference)
                data = self.chapter_reference_re.sub('', data).rstrip()

            # chunk
            chunk = self.dir_link_re.sub('', data)
            rc.write_chunk(chapter, '01', chunk)

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
