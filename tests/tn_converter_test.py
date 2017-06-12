from __future__ import print_function, unicode_literals

import codecs
import os
from unittest import TestCase
import tempfile
import shutil

from converters.tn_converter import TNConverter

class TestConvertTN(TestCase):
    mock_download = None

    def setUp(self):
        self.resource_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources/')

    @staticmethod
    def mock_download_file(url, outfile):
        shutil.copyfile(TestConvertTN.mock_download, outfile)

    def test_convert(self):
        lang = 'en'
        git_repo='https://github.com/Door43/d43-en' #'file://' + self.resource_dir
        out_dir = os.path.join(tempfile.mkdtemp(prefix='testOBS_'), 'rc')

        TestConvertTN.mock_download = os.path.join(self.resource_dir, 'd43-en-master.zip')

        try:
            with TNConverter(lang, git_repo, out_dir, False, TestConvertTN.mock_download_file) as importer:
                importer.run()

                # test output
                self.assertFalse(os.path.isfile(os.path.join(out_dir, '1ch', '01', '00.md')))
                self.assertFalse(os.path.exists(os.path.join(out_dir, '1ch', '00.md')))
                self.assertFalse(os.path.isfile(os.path.join(out_dir, '1ch', '01.md')))

                self.assertTrue(os.path.isfile(os.path.join(out_dir, 'manifest.yaml')))
                self.assertTrue(os.path.isfile(os.path.join(out_dir, 'LICENSE.md')))

                self.assertTrue(os.path.isfile(os.path.join(out_dir, '1ch', '01', '01.md')))
                self.assertTrue(os.path.isfile(os.path.join(out_dir, '1ch', '01', '05.md')))

                self.assertTrue(os.path.isfile(os.path.join(out_dir, '1ch', '01', 'intro.md')))

                general_notes = TNConverter.read_file(os.path.join(out_dir, '1jn', '03', 'intro.md'))
                self.assertNotIn(':en:obe:kt:faith', general_notes)
                self.assertNotIn('00.md', general_notes)
                self.assertIn('/en/tw/dict/bible/kt/faith', general_notes)

                self.assertTrue(os.path.isfile(os.path.join(out_dir, '1ch', 'front', 'intro.md')))

        finally:
            # cleanup
            if( os.path.exists(out_dir)):
                shutil.rmtree(out_dir, ignore_errors=True)
