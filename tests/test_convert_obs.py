from __future__ import print_function, unicode_literals

import codecs
import os
from unittest import TestCase
import tempfile
import shutil

from converters.obs_converter import OBSConverter


class TestImportFromDokuwiki(TestCase):

    def test_import_from_dokuwiki(self):
        """
        This tests the expected conditions
        """
        lang = 'en'
        git_repo = 'file://' + os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources/')
        out_dir = tempfile.mkdtemp(prefix='testOBS_')

        try:
            with OBSConverter(lang, git_repo, out_dir, False) as importer:
                importer.run()

            # check for output files
            self.assertFalse(os.path.isfile(os.path.join(out_dir, 'content', '50.md')))
            self.assertFalse(os.path.isfile(os.path.join(out_dir, 'content', '01.md')))
            self.assertFalse(os.path.isdir(os.path.join(out_dir, 'content', '_front')))
            self.assertFalse(os.path.isdir(os.path.join(out_dir, 'content', '_back')))

            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'manifest.yaml')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', '01', 'title.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', '01', '01.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', '01', 'reference.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', '50', 'title.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', '50', '01.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', '50', 'reference.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', 'front', 'title.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', 'front', 'intro.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', 'back', 'intro.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'LICENSE.md')))

            self.assert_file_contents(os.path.join(out_dir, 'content', 'front', 'title.md'), 'Open Bible Stories')
            self.assert_file_contents(os.path.join(out_dir, 'content', '01', 'title.md'), '1. The Creation')
            self.assert_file_contents(os.path.join(out_dir, 'content', '01', 'reference.md'), 'A Bible story from: Genesis 1-2')

        finally:
            # delete temp files
            if os.path.isdir(out_dir):
                shutil.rmtree(out_dir, ignore_errors=True)

    def test_not_github(self):
        """
        This test the exception when the repository is not on github
        """
        lang = 'en'
        git_repo = 'https://git.door43.org/door43/en-obs'
        out_dir = tempfile.mkdtemp(prefix='testOBS_')

        try:
            with self.assertRaises(Exception) as context:
                with OBSConverter(lang, git_repo, out_dir, False) as importer:
                    importer.run()

            self.assertEqual('Currently only github repositories are supported.', str(context.exception))

        finally:
            # delete temp files
            if os.path.isdir(out_dir):
                shutil.rmtree(out_dir, ignore_errors=True)

    def test_lang_code_not_found(self):
        """
        This test the exception when the repository is not on github
        """
        lang = 'no_lang'
        git_repo = 'file://' + os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources', 'github.com')
        out_dir = tempfile.mkdtemp(prefix='testOBS_')

        try:
            with self.assertRaises(Exception) as context:
                with OBSConverter(lang, git_repo, out_dir, False) as importer:
                    importer.run()

            self.assertEqual('Information for language "{0}" was not found.'.format(lang), str(context.exception))

        finally:
            # delete temp files
            if os.path.isdir(out_dir):
                shutil.rmtree(out_dir, ignore_errors=True)

    def assert_file_contents(self, file, contents):
        """
        Asserts that a file contents the given contents
        :param file: the file to check
        :param contents: the expected contents
        :return:
        """
        with codecs.open(file, 'r', encoding='utf-8') as in_file:
            data = in_file.read()
            self.assertEqual(data, contents, file+' does not contain the expected content')