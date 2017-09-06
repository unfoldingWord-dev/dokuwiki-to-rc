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

    def save_results(self):
        super(OBS_Migration, self).save_results()

        # remove dependent results
        self.remove_results_file("tw_results.json")
        self.remove_results_file("tq_results.json")
        self.remove_results_file("tn_results.json")

    def is_conversion_needed(self, sub_path):
        convert = super(OBS_Migration, self).is_conversion_needed(sub_path)
        if convert and self.last_error and (self.last_error.find('Title not converted error') >= 0):
            convert = False
        return convert

    def not_translated(self, converter):
        if converter:
            return converter.not_translated()
        return False
