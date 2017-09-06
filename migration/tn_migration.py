from __future__ import print_function, unicode_literals

from converters.tn_converter import TNConverter
from migration.migration import Migration


class TN_Migration(Migration):
    """
    Migrates an obs translation from DokuWiki format to Resource Container format if it hasn't yet been done.
    """

    def __init__(self, data, retry_failures):
        super(TN_Migration, self).__init__(data, retry_failures)
        self.create_keys('tn')

    def run(self):
        obs_success = self.read_obs_success()
        if obs_success:
            print("\nConverting TN in: " + self.name)
            return self.do_conversion(self.type, 'content')
        else:
            msg = "Skipping over TN since OBS Failed: " + self.name
            print(msg)
            self.set_error(msg)

        return False

    def init_converter(self, lang_code, git_repo, out_dir, quiet):
        return TNConverter(lang_code, git_repo, out_dir, quiet, overwrite=True, ignore_lang_code_error=True)
