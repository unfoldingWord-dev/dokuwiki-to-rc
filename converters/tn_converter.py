# -*- coding: utf-8 -*-

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
from file_utils import write_file, unzip
from url_utils import get_languages, join_url_parts, get_url, download_file
from converters.common import quiet_print, dokuwiki_to_markdown, ResourceManifest, ResourceManifestEncoder, en_book_names

class TNConverter(object):

    heading_re = re.compile(r'^=+', re.UNICODE | re.MULTILINE)
    notes_heading_re = re.compile(r'^ *translationNotes', re.UNICODE)
    words_heading_re = re.compile(r'^ *translationWords', re.UNICODE)
    notes_re = re.compile(r' *\* +\*\*([^\*]+)\*\*( +-+ +)?(.*)', re.UNICODE | re.MULTILINE)
    general_re = re.compile(r'(General Information:?)|(Connecting Statement:?)', re.UNICODE | re.IGNORECASE)

    link_tag_re = re.compile(r'\[\[\:(((?!\[|\]).)*)\]\]', re.UNICODE)

    link_ta_re = re.compile(r'\[\[\:*\:en\:*\:ta\:*\:vol(1|2)\s*\:*\:\s*(\w+)\s*\:*\:\s*(\w+)\]\]', re.UNICODE | re.IGNORECASE)
    link_titled_ta_re = re.compile(r'\[\[\:*\:en\:*\:ta\:*\:vol(1|2)\s*\:*\:\s*(\w+)\s*\:*\:\s*(\w+)\|\s*([\d\-\–\: \w,\.]+)\s*\]\]', re.UNICODE | re.IGNORECASE)
    link_titled_notes_re = re.compile(r'\[\[\:*\:en\:bible\:*\:notes\:*\:(\w+)\:*\:(\w+)\:*\:(\w+)\s*\|\s*([\d\-\–\: \w,\.\/<>]+)\s*\]\]', re.UNICODE | re.IGNORECASE)
    link_notes_re = re.compile(r'\[\[\:*\:en\:*\:bible\:*\:notes\:*\:(\w+)\:*\:(\w+)\:*\:(\w+)\s*\]\]', re.UNICODE | re.IGNORECASE)
    link_words_re = re.compile(r'\[\[\:*\:en\:*\:obe\:*\:(\w+)\:*\:(\w+)\s*\]\]', re.UNICODE | re.IGNORECASE)
    link_broken_titled_notes_re = re.compile(r'\[\[\:*\:en\:*\:bible\:*\:(\w+)\:*\:(\w+)\:*\:(\w+)\s*\|\s*([\d\-\–\: \w,\.\/<>]+)\s*\]\]', re.UNICODE | re.IGNORECASE)


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

        self.lang_code = self.lang_data['lc'].lower()

        # remove trailing slash
        if self.git_repo[-1:] == '/':
            self.git_repo = self.git_repo[:-1]

        self.temp_dir = tempfile.mkdtemp('', 'tn', None)
        self.repo_file = os.path.join(self.temp_dir, 'tn.zip')
        # tricky: github gives lowercase dir names in zip archive
        self.repo_dir = os.path.join(self.temp_dir, 'd43-{}-master'.format(self.lang_code))
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
                'title': '{} translationNotes'.format(en_book_names[book]),
                'versification': ''
            })
            chapters = next(os.walk(os.path.join(source_dir, book)))[1]
            for chapter in chapters:
                if chapter == '00' or chapter == '000':
                    # write book intro file
                    book_chunk_file = os.path.join(source_dir, book, chapter, 'intro.txt')
                    if os.path.exists(book_chunk_file):
                        content = dokuwiki_to_markdown(TNConverter.read_file(book_chunk_file))
                        content = self.process_links(book, chapter, 'intro', content)
                        new_book_intro_file = os.path.join(target_dir, book, 'front', 'intro.md')
                        content = self.clean_intro(content)
                        if content.strip() != '':
                            write_file(new_book_intro_file, content.strip())
                    continue

                chunks = next(os.walk(os.path.join(source_dir, book, chapter)))[2]
                for chunk in chunks:
                    chunk_file = os.path.join(source_dir, book, chapter, chunk)
                    try:
                        if chunk == '00.txt' or chunk == '000.txt':
                            # write chapter intro file
                            content = dokuwiki_to_markdown(TNConverter.read_file(chunk_file))
                            content = self.process_links(book, chapter, chunk.split('.')[0], content)
                            new_intro_file = os.path.join(target_dir, book, chapter, 'intro.md')
                            content = self.clean_intro(content)
                            if content.strip() != '':
                                write_file(new_intro_file, content.strip())
                        else:
                            # parse chunk notes
                            content = TNConverter.read_file(chunk_file)
                            blocks = TNConverter.heading_re.split(content)
                            notes = ''
                            words = ''
                            for block in blocks:
                                if TNConverter.notes_heading_re.match(block):
                                    if chapter == '00' or chapter == '000':
                                        print('WARNING: processing chapter 00')
                                    if chunk == '00.txt' == '000.txt':
                                        print('WARNING: processing chunk 00')
                                    for note in TNConverter.notes_re.finditer(block):
                                        note_body = self.process_links(book, chapter, chunk.split('.')[0], note.group(3).strip())
                                        notes += '# {}\n\n{}\n\n'.format(note.group(1).strip(), note_body)
                                elif TNConverter.words_heading_re.match(block):
                                    for link in TNConverter.link_words_re.finditer(block):
                                        words = words + '\n* [[rc://en/tw/dict/bible/{}/{}]]'.format(link.group(1), link.group(2))

                            new_chunk_file = os.path.join(target_dir, book, chapter, chunk.replace('.txt', '.md'))
                            if notes.strip() != '':
                                if words.strip():
                                    notes = '{}\n\n# translationWords\n\n{}'.format(notes.strip(), words.strip())
                                write_file(new_chunk_file, notes.strip())
                            elif words.strip() != '':
                                # TRICKY: write tW even if there are no notes
                                print('found tW without notes')
                                notes = '{}\n\n# translationWords\n\n{}'.format(notes.strip(), words.strip())
                                write_file(new_chunk_file, notes.strip())

                    except Exception as e:
                        print('ERROR: {}/{}/{}: {}'.format(book, chapter, chunk, e))
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

    def clean_intro(self, content):
        re_discussion = re.compile('~~discussion~~', re.IGNORECASE | re.MULTILINE)
        re_nocache = re.compile('~~nocache~~', re.IGNORECASE | re.MULTILINE)
        re_tags = re.compile('{{tag>.*}}', re.IGNORECASE | re.MULTILINE)

        content = re_discussion.sub('', content)
        content = re_nocache.sub('', content)
        content = re_tags.sub('', content)

        return content

    def process_links(self, book, chapter, chunk, text):
        text = re.sub(self.link_titled_ta_re, lambda m: self.format_titled_ta_link(m), text)
        text = re.sub(self.link_ta_re, lambda m: self.format_ta_link(m), text)
        text = re.sub(self.link_titled_notes_re, lambda m: self.format_titled_note_link(book, chapter, chunk, m), text)
        text = re.sub(self.link_notes_re, lambda m: self.format_note_link(book, chapter, chunk, m), text)
        text = re.sub(self.link_words_re, lambda m: self.format_word_link(m), text)
        text = re.sub(self.link_broken_titled_notes_re, lambda m: self.format_titled_note_link(book, chapter, chunk, m), text)

        if self.link_tag_re.search(text):
            print('ERROR: Unknown link at {}/{}/{}: {}'.format(book, chapter, chunk, text))
        return text

    # def format_titled_bible_link(self, match):
    #     return '[{}](/en/ulb/book/{}/{}/{})'.format(match.group(4), match.group(1), match.group(2), match.group(3))

    def format_word_link(self, match):
        if(match.group(1) == 'kt'):
            return '[[rc://en/tw/dict/bible/kt/{}]]'.format(match.group(2))
        else:
            return '[[rc://en/tw/dict/bible/other/{}]]'.format(match.group(2))

    def format_titled_ta_link(self, match):
        return '[{}](rc://en/ta/man/{}/{})'.format(match.group(4), match.group(2).replace('_', '-'), match.group(3).replace('_', '-'))

    def format_ta_link(self, match):
        return '[[rc://en/ta/man/{}/{}]]'.format(match.group(2).replace('_', '-'), match.group(3).replace('_', '-'))

    def format_titled_note_link(self, book, chapter, chunk, match):
        bookTitle = en_book_names[match.group(1)]
        match_chapter = match.group(2)
        if match_chapter == '00' or match_chapter == '000':
            match_chapter = 'front'
        match_chunk = match.group(3)
        if match_chunk == '00' or match_chunk == '000':
            match_chunk = 'intro'

        if '<<' in  match.group(4) or '>>' in match.group(4)\
                or bookTitle in match.group(4):
            title = match.group(4)
        else:
            title = '{} {}'.format(bookTitle, match.group(4))

        if book == match.group(1):
            if chapter == match_chapter:
                return '[{}](./{}.md)'.format(title, match_chunk)
            else:
                return '[{}](../{}/{}.md)'.format(title, match_chapter, match_chunk)
        else:
            print('WARNING: linking to a different book at {}/{}/{}: {}'.format(book, chapter, chunk, match.group(0)))
            return '[{}](../../{}/{}/{}.md)'.format(title, match.group(1), match_chapter, match_chunk)

    def format_note_link(self, book, chapter, chunk, match):
        bookTitle = en_book_names[match.group(1)]
        match_chapter = match.group(2)
        if match_chapter == '00' or match_chapter == '000':
            match_chapter = 'front'
            match_chapter_formatted = match_chapter
        else:
            match_chapter_formatted = self.format_number(match_chapter)

        match_chunk = match.group(3)
        if match_chunk == '00' or match_chunk == '000':
            match_chunk = 'intro'
            match_chunk_formatted = match_chunk
        else:
            match_chunk_formatted = self.format_number(match_chunk)

        if match_chapter == 'front':
            verseTitle = '{}'.format(match_chunk_formatted)
        else:
            verseTitle = '{}:{}'.format(match_chapter_formatted, match_chunk_formatted)

        if book == match.group(1):
            if chapter == match_chapter:
                return '[{} {}](./{}.md)'.format(bookTitle, verseTitle, match_chunk)
            else:
                return '[{} {}](../{}/{}.md)'.format(bookTitle, verseTitle, match_chapter, match_chunk)
        else:
            print('WARNING: linking to a different book at {}/{}/{}: {}'.format(book, chapter, chunk, match.group(0)))
            return '[{} {}](../../{}/{}/{}.md)'.format(bookTitle, verseTitle, match.group(1), match_chapter, match_chunk)

    def format_number(self, str):
        """
        Attempts to format a string as an integer.
        if it fails the string will be returned
        :param str:
        :return:
        """
        try:
            return int(str)
        except:
            return str.strip()

    @staticmethod
    def read_file(file_name, encoding='utf-8-sig'):
        with codecs.open(file_name, 'r', encoding=encoding) as f:
            return f.read()