from __future__ import print_function, unicode_literals
from converters.obs_converter import OBSConverter
from migration.migration import Migration


class OBS_Migration(Migration):
    """
    Migrates an obs translation from DokuWiki format to Resource Container format if it hasn't yet been done.
    """

    def __init__(self, data, retry_failures):
        super(OBS_Migration, self).__init__(data, retry_failures)
        self.create_keys('obs')

    def run(self):
        return self.do_conversion(self.type, 'content')

    def init_converter(self, lang_code, git_repo, out_dir, quiet):
        return OBSConverter(lang_code, git_repo, out_dir, quiet, flat_format=True)

    def not_translated(self, converter):
        if converter:
            return converter.not_translated()
        return False
