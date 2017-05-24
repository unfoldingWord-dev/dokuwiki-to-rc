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
                self.assertFalse(os.path.isfile(os.path.join(out_dir, 'gen', '01', '00.md')))
                self.assertFalse(os.path.exists(os.path.join(out_dir, 'gen', '00.md')))
                self.assertFalse(os.path.isfile(os.path.join(out_dir, 'gen', '01.md')))

                self.assertTrue(os.path.isfile(os.path.join(out_dir, 'manifest.yaml')))
                self.assertTrue(os.path.isfile(os.path.join(out_dir, 'LICENSE.md')))

                self.assertTrue(os.path.isfile(os.path.join(out_dir, 'gen', '01', '01.md')))
                self.assertTrue(os.path.isfile(os.path.join(out_dir, 'gen', '01', '03.md')))

        finally:
            # cleanup
            if( os.path.exists(out_dir)):
                shutil.rmtree(out_dir, ignore_errors=True)
