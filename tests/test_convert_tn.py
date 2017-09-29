from __future__ import print_function, unicode_literals
import os
from unittest import TestCase
import tempfile
import shutil
from converters.tn_converter import TNConverter


class TestOBStNFromDokuwiki(TestCase):

    def test_obs_tn_from_dokuwiki(self):
        """
        This tests the expected conditions
        """
        lang = 'en'
        git_repo = 'file://' + os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources/')
        out_dir = tempfile.mkdtemp(prefix='testOBStN_')

        try:
            with TNConverter(lang, git_repo, out_dir, False, True) as importer:
                importer.run()

            # check for output files
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'package.json')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', '01', '01.md')))
            self.assertTrue(os.path.isfile(os.path.join(out_dir, 'content', '50', '17.md')))

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
        out_dir = tempfile.mkdtemp(prefix='testOBStN_')

        try:
            with self.assertRaises(Exception) as context:
                with TNConverter(lang, git_repo, out_dir, False, True) as importer:
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
        git_repo = 'file://' + os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources/')
        out_dir = tempfile.mkdtemp(prefix='testOBS_')

        try:
            with self.assertRaises(Exception) as context:
                with TNConverter(lang, git_repo, out_dir, False, True) as importer:
                    importer.run()

            self.assertEqual('Information for language "{0}" was not found.'.format(lang), str(context.exception))

        finally:
            # delete temp files
            if os.path.isdir(out_dir):
                shutil.rmtree(out_dir, ignore_errors=True)
