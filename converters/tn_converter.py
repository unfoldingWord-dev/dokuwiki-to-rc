from __future__ import print_function, unicode_literals

import codecs
import inspect
import tempfile
import json
import shutil
import os
import re
from general_tools.file_utils import write_file, unzip
from general_tools.url_utils import get_languages, join_url_parts, get_url, download_file
from converters.common import quiet_print, dokuwiki_to_markdown, ResourceManifest, ResourceManifestEncoder

class TNConverter(object):

    tag_re = re.compile(r'\{\{tag>.*?\}\}', re.UNICODE)
    squiggly_re = re.compile(r'~~(?:DISCUSSION|NOCACHE)~~', re.UNICODE)
    extra_blanks_re = re.compile(r'\n{3,}', re.UNICODE)
    chapter_link_re = re.compile(r'\[\[:en:bible:questions:comprehension:(.*?):home\|(.*?)\]\]', re.UNICODE)
    missing_blank_line_re = re.compile(r'(\n    \*.*\n)(__)', re.UNICODE)
    story_num_re = re.compile(r'(Story )#', re.UNICODE)
    navigate_re = re.compile(r'\[\[:en:obs:notes:questions:(.*?)\|\s*(.*?)\s*\]\]', re.UNICODE)
    navigate2_re = re.compile(r'\[\[en/obs/notes/questions/(.*?)\|\s*(.*?)\s*\]\]', re.UNICODE)

    heading_re = re.compile(r'^=+', re.UNICODE)
    notes_re = re.compile(r'^ *translationNotes', re.UNICODE)

    def __init__(self, lang_code, git_repo, out_dir, quiet=True, download_handler=None):
        """
        
        :param lang_code: 
        :param git_repo: 
        :param out_dir: 
        :param quiet: 
        :param download_handler: provided for unit tests
        """
        self.git_repo = git_repo
        self.quiet = quiet
        self.out_dir = out_dir

        if not download_handler:
            self.download_file = download_file
        else:
            self.download_file = download_handler

        if 'github' not in git_repo and 'file://' not in git_repo:
            raise Exception('Currently only github repositories are supported.')

        # get the language data
        quiet_print(self.quiet, 'Downloading language data...', end=' ')
        langs = get_languages()
        quiet_print(self.quiet, 'finished.')

        self.lang_data = next((l for l in langs if l['lc'] == lang_code), '')

        if not self.lang_data:
            raise Exception('Information for language "{0}" was not found.'.format(lang_code))

        # read the github access token
        root_dir = os.path.dirname(os.path.dirname(inspect.stack()[0][1]))
        with codecs.open(os.path.join(root_dir, 'github_api_token'), 'r', 'utf-8-sig') as in_file:
            # read the text from the file
            self.access_token = in_file.read()

        lang_code = self.lang_data['lc']

        # remove trailing slash
        if self.git_repo[-1:] == '/':
            self.git_repo = self.git_repo[:-1]

        self.temp_dir = tempfile.mkdtemp('', 'tn', None)
        self.repo_file = os.path.join(self.temp_dir, 'tn.zip')
        # tricky: github gives lowercase dir names in zip archive
        self.repo_dir = os.path.join(self.temp_dir, 'd43-{}-master'.format(lang_code.lower()))
        self.repo_zip_url = join_url_parts(self.git_repo, 'archive/master.zip')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def run(self):

        # download repo
        try:
            print('Downloading {0}...'.format(self.repo_zip_url))
            self.download_file(self.repo_zip_url, self.repo_file)
        finally:
            print('finished.')

        self.unzip_repo_file(self.repo_file, self.temp_dir)

        if not os.path.isdir(self.repo_dir):
            raise Exception('Was not able to find {0}'.format(self.repo_dir))

        # get the source files from the git repository
        bible_notes_dir = join_url_parts(self.repo_dir, 'bible/notes')
        obs_notes_dir = join_url_parts(self.repo_dir, 'obs/notes')

        # build bible RC
        target_dir = os.path.join(self.out_dir, 'bible')
        self.process_bible_notes(bible_notes_dir, target_dir)

        # build obs RC
        target_dir = os.path.join(self.out_dir, 'obs')
        self.process_obs_notes(obs_notes_dir, target_dir)

    def unzip_repo_file(self, repo_file, repo_dir):
        try:
            print('Unzipping {0}...'.format(repo_file))
            unzip(repo_file, repo_dir)
        finally:
            print('finished.')

    def process_bible_notes(self, source_dir, target_dir):
        books = next(os.walk(source_dir))[1]
        for book in books:
            chapters = next(os.walk(os.path.join(source_dir, book)))[1]
            for chapter in chapters:
                if chapter == '00':
                    print('WARNING: processing chapter 00')
                chunks = next(os.walk(os.path.join(source_dir, book, chapter)))[2]
                for chunk in chunks:
                    if chunk == '00.txt':
                        print('WARNING: processing chunk 00')
                    # parse notes
                    chunk_file = os.path.join(source_dir, book, chapter, chunk)
                    try:
                        content = self.read_file(chunk_file)
                        blocks = TNConverter.heading_re.split(content)
                        for block in blocks:
                            if TNConverter.notes_re.match(block):
                                print(block)
                    except Exception as e:
                        print(e)


    def process_obs_notes(self, source_dir, target_dir):
        pass

    def read_file(file_name, encoding='utf-8'):
        with codecs.open(file_name, 'r', encoding=encoding) as f:
            return f.read()