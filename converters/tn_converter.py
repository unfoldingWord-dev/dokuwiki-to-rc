from __future__ import print_function, unicode_literals

import codecs
import inspect
import tempfile
import json
import shutil
import os
import yaml
import re
from .unicode_utils import to_str
from datetime import datetime
from general_tools.file_utils import write_file, unzip
from general_tools.url_utils import get_languages, join_url_parts, get_url, download_file
from converters.common import quiet_print, dokuwiki_to_markdown, ResourceManifest, ResourceManifestEncoder

class TNConverter(object):

    heading_re = re.compile(r'^=+', re.UNICODE | re.MULTILINE)
    notes_heading_re = re.compile(r'^ *translationNotes', re.UNICODE)
    notes_re = re.compile(r' *\* +\*\*([^\*]+)\*\*( +-+ +)?(.*)', re.UNICODE | re.MULTILINE)
    general_re = re.compile(r'(General Information:?)|(Connecting Statement:?)', re.UNICODE | re.IGNORECASE)

    link_tag_re = re.compile(r'\[\[\:(((?!\[|\]).)*)\]\]', re.UNICODE)

    link_ta_re = re.compile(r'\[\[\:*\:en\:*\:ta\:*\:vol(1|2)\s*\:*\:\s*(\w+)\s*\:*\:\s*(\w+)\]\]', re.UNICODE | re.IGNORECASE)
    link_titled_ta_re = re.compile(r'\[\[\:*\:en\:*\:ta\:*\:vol(1|2)\s*\:*\:\s*(\w+)\s*\:*\:\s*(\w+)\|\s*([\d\-\: \w,\.]+)\s*\]\]', re.UNICODE | re.IGNORECASE)
    link_titled_notes_re = re.compile(r'\[\[\:?\:en\:bible\:notes\:(\w+)\:(\w+)\:(\w+)\s*\|\s*([\d\-\: \w,\.\/]+)\s*\]\]', re.UNICODE | re.IGNORECASE)
    link_notes_re = re.compile(r'\[\[\:?\:en\:bible\:notes\:(\w+)\:(\w+)\:(\w+)\s*\]\]', re.UNICODE | re.IGNORECASE)


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

        # build bible RC
        self.process_bible_notes(bible_notes_dir, self.out_dir)

    def unzip_repo_file(self, repo_file, repo_dir):
        try:
            print('Unzipping {0}...'.format(repo_file))
            unzip(repo_file, repo_dir)
        finally:
            print('finished.')

    def process_bible_notes(self, source_dir, target_dir):
        books = next(os.walk(source_dir))[1]
        projects = []
        for book in books:
            projects.append({
                'categories': [],
                'identifier': book,
                'path': './{}'.format(book),
                'sort': 0,
                'title': 'translationNotes',
                'versification': ''
            })
            chapters = next(os.walk(os.path.join(source_dir, book)))[1]
            for chapter in chapters:
                chunks = next(os.walk(os.path.join(source_dir, book, chapter)))[2]
                for chunk in chunks:
                    # parse notes
                    chunk_file = os.path.join(source_dir, book, chapter, chunk)
                    try:
                        content = TNConverter.read_file(chunk_file)
                        blocks = TNConverter.heading_re.split(content)
                        notes = ''
                        for block in blocks:
                            if TNConverter.notes_heading_re.match(block):
                                if chapter == '00':
                                    print('WARNING: processing chapter 00')
                                if chunk == '00.txt':
                                    print('WARNING: processing chunk 00')
                                for note in TNConverter.notes_re.finditer(block):
                                    note_body = self.process_links(book, chapter, chunk.split('.')[0], note.group(3).strip())
                                    notes += '# {}\n\n{}\n\n'.format(note.group(1).strip(), note_body)
                        new_chunk_file = os.path.join(target_dir, book, chapter, chunk.replace('.txt', '.md'))
                        if notes.strip() != '':
                            write_file(new_chunk_file, notes.strip())
                    except Exception as e:
                        print(e)
        # write the license
        dir_path = os.path.dirname(os.path.realpath(__file__))
        shutil.copy(os.path.join(dir_path, 'OBS_LICENSE.md'), os.path.join(self.out_dir, 'LICENSE.md'))

        # write manifest
        new_manifest = {
            'dublin_core': {
                'conformsto': 'rc0.2',
                'contributor': [
                    'Wycliffe Associates'
                ],
                'creator': 'Wycliffe Associates',
                'description': 'Notes to help translators of the Bible',
                'format': 'text/markdown',
                'identifier': 'tn',
                'issued': '?',
                'language': {
                    'direction': self.lang_data['ld'],
                    'identifier': self.lang_data['lc'],
                    'title': self.lang_data['ang']
                },
                'modified': datetime.today().strftime('%Y-%m-%d'),
                'publisher': 'unfoldingWord',
                'relation': [
                    'en/ulb',
                    'en/udb'
                ],
                'rights': 'CC BY-SA 4.0',
                'source': [{
                    'identifier': 'tn',
                    'language': self.lang_data['lc'],
                    'version': '?'
                }],
                'subject': 'Translator Notes',
                'title': 'translationNotes',
                'type': 'help',
                'version': '?'
            },
            'checking': {
                'checking_entity': [
                    'Wycliffe Associates'
                ],
                'checking_level': 3
            },
            'projects': projects
        }

        new_manifest = to_str(new_manifest)
        write_file(os.path.join(self.out_dir, 'manifest.yaml'), yaml.dump(new_manifest, default_flow_style=False))

    def process_links(self, book, chapter, chunk, text):
        text = re.sub(self.link_titled_ta_re, lambda m: self.format_titled_ta_link(book, chapter, chunk, m), text)
        text = re.sub(self.link_ta_re, lambda m: self.format_ta_link(book, chapter, chunk, m), text)
        text = re.sub(self.link_titled_notes_re, lambda m: self.format_titled_note_link(book, chapter, chunk, m), text)
        text = re.sub(self.link_notes_re, lambda m: self.format_note_link(book, chapter, chunk, m), text)
        if self.link_tag_re.search(text):
            print('ERROR: Unknown link at {}/{}/{}: {}'.format(book, chapter, chunk, text))
        return text

    def format_titled_ta_link(self, book, chapter, chunk, match):
        return '[{}](/en/ta/{}/{})'.format(match.group(4), match.group(2), match.group(3))

    def format_ta_link(self, book, chapter, chunk, match):
        return '[[/en/ta/{}/{}]]'.format(match.group(2), match.group(3))

    def format_titled_note_link(self, book, chapter, chunk, match):
        bookTitle = match.group(1) # get title
        if book == match.group(1):
            if chapter == match.group(2):
                return '[{} {}](./{}.md)'.format(bookTitle, match.group(4), match.group(3))
            else:
                return '[{} {}](../{}/{}.md)'.format(bookTitle, match.group(4), match.group(2), match.group(3))
        else:
            print('WARNING: linking to a different book at {}/{}/{}: {}'.format(book, chapter, chunk, match.group(0)))
            return '[{} {}](../../{}/{}/{}.md)'.format(bookTitle, match.group(4), match.group(1), match.group(2), match.group(3))

    def format_note_link(self, book, chapter, chunk, match):
        bookTitle = match.group(1) # get title
        verseTitle = '{}:{}'.format(int(match.group(2)), int(match.group(3)))
        if book == match.group(1):
            if chapter == match.group(2):
                return '[{} {}](./{}.md)'.format(bookTitle, verseTitle, match.group(3))
            else:
                return '[{} {}](../{}/{}.md)'.format(bookTitle, verseTitle, match.group(2), match.group(3))
        else:
            print('WARNING: linking to a different book at {}/{}/{}: {}'.format(book, chapter, chunk, match.group(0)))
            return '[{} {}](../../{}/{}/{}.md)'.format(bookTitle, verseTitle, match.group(1), match.group(2), match.group(3))


    @staticmethod
    def read_file(file_name, encoding='utf-8-sig'):
        with codecs.open(file_name, 'r', encoding=encoding) as f:
            return f.read()