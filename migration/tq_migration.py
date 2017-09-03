from __future__ import print_function, unicode_literals

from converters.tq_converter import TQConverter
from migration.migration import Migration


class TQ_Migration(Migration):
    """
    Migrates an obs translation from DokuWiki format to Resource Container format if it hasn't yet been done.
    """

    def __init__(self, data, retry_failures):
        super(TQ_Migration, self).__init__(data, retry_failures)
        self.create_keys('tq')

    def run(self):
        obs_success = self.read_obs_success()
        if obs_success:
            print("\nConverting TQ in: " + self.name)
            return self.do_conversion(self.type, 'content')
        else:
            msg = "Skipping over TQ since OBS Failed: " + self.name
            print(msg)
            self.set_error(msg)

        return False

    def init_converter(self, lang_code, git_repo, out_dir, quiet):
        return TQConverter(lang_code, git_repo, None, out_dir, quiet)
