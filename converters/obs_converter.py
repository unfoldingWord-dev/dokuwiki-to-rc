from __future__ import print_function, unicode_literals

import codecs
import os
import re
from general_tools import file_utils
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
    langs = None

    def __init__(self, lang_code, git_repo, out_dir, quiet, flat_format=False, ignore_lang_code_error=False):
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
        if OBSConverter.langs:  # check if cached
            langs = OBSConverter.langs
        else:
            try:
                quiet_print(self.quiet, 'Downloading language data...', end=' ')
                langs = get_languages()
                OBSConverter.langs = langs
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

        lang_code = self.lang_data['lc']

        # remove trailing slash
        if self.git_repo[-1:] == '/':
            self.git_repo = self.git_repo[:-1]

        # get the source files from the git repository
        base_url = self.git_repo.replace('github.com', 'raw.githubusercontent.com')

        # download front and back matter
        self.trying = 'downloading front and back matter'
        front_path = os.path.join(self.download_dir, 'content', 'front', 'intro.md')
        self.download_obs_file(base_url, 'front-matter.txt', front_path)
        back_path = os.path.join(self.download_dir, 'content', 'back', 'intro.md')
        self.download_obs_file(base_url, 'back-matter.txt', back_path)

        # book title
        self.trying = 'getting title'
        title = ''
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

        status = self.get_uw_status(lang_code)

        manifest = OBSManifest()

        self.trying = 'creating manifest'
        new_manifest = {
            'dublin_core': {
                'title': title,
                'type': 'book',
                'format': 'text/markdown',
                'contributor': [
                    'Distant Shores Media',
                    'Door43 World Missions Community'
                ],
                'creator': 'Distant Shores Media',
                'description': '50 key stories of the Bible, from Creation to Revelation, for evangelism & discipleship, in text, audio, and video, on any mobile phone, in any language, for free. It increases understanding of the historical and redemptive narrative of the entire Bible.',
                'identifier': manifest.resource['slug'],
                'language': {
                    'direction': self.lang_data['ld'],
                    'identifier': status['source_text'],
                    'title': self.lang_data['ang']
                },
                'modified': datetime.today().strftime('%Y-%m-%d'),
                'publisher': 'unfoldingWord',
                'relation': [
                    'en/tw',
                    'en/obs-tq',
                    'en/obs-tn'
                ],
                'source': [{
                    'identifier': manifest.resource['slug'],
                    'language': manifest.language['slug'],
                    'version': status['source_text_version']
                }],
                'subject': 'Bible stories',
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
            self.trying = 'converting: ' + file_to_download
            chapter_file = os.path.join(story_dir, file_to_download)
            self.download_obs_file(base_url, file_to_download, chapter_file)
            # split chapters into chunks
            chapter_slug = file_to_download.replace('.txt', '')
            self.chunk_chapter(rc, chapter_file, chapter_slug)
            os.remove(chapter_file)

        self.trying = 'writing book info'
        rc.write_chunk('front', 'title', title)
        rc.write_chunk('front', 'intro', codecs.open(front_path, 'r', encoding='utf-8').read())
        rc.write_chunk('back', 'intro', codecs.open(back_path, 'r', encoding='utf-8').read())
        dir_path = os.path.dirname(os.path.realpath(__file__))
        shutil.copy(os.path.join(dir_path, 'OBS_LICENSE.md'), os.path.join(self.out_dir, 'LICENSE.md'))

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

    def chunk_chapter(self, rc, chapter_file, chapter):
        with codecs.open(chapter_file, 'r', encoding='utf-8') as in_file:
            data = in_file.read()

            if not self.flat_format:
                # title
                if self.chapter_title_re.search(data):
                    title = self.chapter_title_re.search(data).group(1).rstrip()
                    print('TITLE: ', title)
                    self.test_for_translated_title(title)
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

            else:
                if self.chapter_title_re.search(data):
                    title = self.chapter_title_re.search(data).group(1).rstrip()
                    print('TITLE: ', title)
                    self.test_for_translated_title(title)

                # chunk
                rc.write_chunk('.', chapter, data)

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

    def test_for_translated_title(self, text):
        if not self.english and (self.translated_titles == 0):
            for english_title in english_titles:
                if text.find(english_title) >= 0:
                    return
            self.translated_titles += 1

    def not_translated(self):
        return not self.english and self.translated_titles == 0

english_titles = [
    'The Creation',
    'Sin Enters the World',
    'The Flood',
    'God’s Covenant with Abraham',
    'The Son of Promise',
    'God Provides for Isaac',
    'God Blesses Jacob',
    'God Blessed Jacob',
    'God Saves Joseph and His Family',
    'God Calls Moses',
    'The Ten Plagues',
    'The Passover',
    'The Exodus',
    'God’s Covenant with Israel',
    'Wandering in the Wilderness',
    'The Promised Land',
    'The Deliverers',
    'God’s Covenant with David',
    'The Divided Kingdom',
    'The Prophets',
    'The Exile and Return',
    'God Promises the Messiah',
    'The Birth of John',
    'The Birth of Jesus',
    'John Baptizes Jesus',
    'Satan Tempts Jesus',
    'Jesus Starts His Ministry',
    'The Story of the Good Samaritan',
    'The Rich Young Ruler',
    'The Story of the Unmerciful Servant',
    'Jesus Feeds Five Thousand People',
    'Jesus Walks on Water',
    'Jesus Heals a Demon-Possessed Man & a Sick Woman',
    'The Story of the Farmer',
    'Jesus Teaches Other Stories',
    'The Story of the Compassionate Father',
    'The Transfiguration',
    'Jesus Raises Lazarus from the Dead',
    'Jesus Is Betrayed',
    'Jesus Is Put on Trial',
    'Jesus Is Crucified',
    'God Raises Jesus from the Dead',
    'Jesus Returns to Heaven',
    'The Church Begins',
    'Peter and John Heal a Beggar',
    'Stephen and Philip',
    'Paul Becomes a Christian',
    'Paul and Silas in Philippi',
    'Jesus Is the Promised Messiah',
    'God’s New Covenant',
    'Jesus Returns',
    'Philip and the Ethiopian Official'
]