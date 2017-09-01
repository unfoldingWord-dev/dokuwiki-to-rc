from __future__ import print_function, unicode_literals

import os
from general_tools import file_utils


class Migration(object):
    """
    Base class for Migrating a translation from DokuWiki format to Resource Container format if it hasn't yet been done.
    """

    def __init__(self, data, retry_failures):
        self.lang = data['lc']
        self.lang_folder = data['lang_folder']
        self.repo_url = data['repo_url']
        self.name = data['name']
        self.data = data
        self.error = None
        self.destination = None
        self.results_prefix = ''
        self.error_key = 'error'
        self.success_key = 'success'
        self.retry_failures = retry_failures

    def run(self):
        pass

    def create_keys(self, prefix):
        self.results_prefix = prefix
        self.error_key = prefix + 'error'
        self.success_key = prefix + 'success'

    def save_results(self):
        path = self.get_results_path()
        file_utils.write_file(path, self.data)

    def read_results(self):
        path = self.get_results_path()
        results = file_utils.load_json_object(path)
        return results

    def get_last_success(self):
        results = self.read_results()
        if not results:
            return False
        success = results[self.success_key]
        return success

    def get_results_path(self):
        path = os.path.join(self.lang_folder, self.results_prefix + "results.json")
        return path

    def set_error(self, msg):
        self.data[self.success_key] = False
        self.data[self.error_key] = msg
        print("\nError converting " + self.results_prefix + self.lang + ":\n" + msg)
        self.save_results()

    def set_success(self, success):
        self.data[self.error_key] = None
        self.data[self.success_key] = success
        self.save_results()

    def is_conversion_needed(self, sub_path):
        exists = os.path.exists(os.path.join(self.destination, sub_path))
        results = self.read_results()
        last_success = False if not results else results[self.success_key]
        error_retry = not last_success and self.retry_failures

        if exists:
            convert = error_retry  # if last conversion failed, retry if directed
        else:
            convert = (not results) or error_retry  # if there are no results, presume new conversion
        return convert

    def do_conversion(self, migration_folder, sub_path, conversion_class):
        self.destination = os.path.join(self.lang_folder, migration_folder)
        convert = self.is_conversion_needed(sub_path)
        if convert:
            file_utils.make_dir(self.destination)

            converter = None
            try:
                converter = conversion_class(self.lang, self.repo_url, self.destination, False)
                converter.run()
                self.set_success(True)
                return True

            except Exception as e:
                step = "Init" if not converter else converter.trying
                msg = "Failed doing '" + step + "', error: " + str(e)
                self.set_error(msg)
        else:
            print("\nSkipping over already converted OBS in " + self.name)
            return True

        return False
