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
        self.type = ''
        self.results_prefix = ''
        self.error_key = 'error'
        self.success_key = 'success'
        self.retry_failures = retry_failures
        self.final_data = None
        self.last_success = False
        self.last_error = None

    def run(self):
        pass

    def create_keys(self, type):
        self.type = type
        prefix = type + '_'
        self.results_prefix = prefix
        self.error_key = prefix + 'error'
        self.success_key = prefix + 'success'

    def save_results(self):
        path = self.get_results_path()
        self.final_data = self.data
        file_utils.write_file(path, self.data)

    def clear_results(self):
        path = self.get_results_path()
        try:
            os.remove(path)
        except:
            pass
        self.final_data = None

    def read_results(self):
        path = self.get_results_path()
        results = file_utils.load_json_object(path)
        self.final_data = results
        return results

    def read_obs_results(self):
        path = os.path.join(self.lang_folder, "obs_results.json")
        results = file_utils.load_json_object(path)
        return results

    def read_obs_success(self):
        results = self.read_obs_results()
        success = False if not results else results["obs_success"]
        return success

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
        self.last_success = last_success
        self.last_error = None if not results else results[self.error_key]

        convert = False
        if exists:
            if not last_success and self.retry_failures:   # if last conversion failed, retry if selected
                convert = True
            # convert = True  # TODO remove force
        else:
            if not results:  # if there are no results, presume this is new conversion
                convert = True

            elif last_success:  # if last results says success, but output folder missing, redo conversion
                convert = True

            # if there was an error last time and retry_failures selected, reconvert
            elif not last_success and self.retry_failures:
                convert = True

        return convert

    def init_converter(self, lang_code, git_repo, out_dir, quiet):
        return None

    def not_translated(self, converter):
        return False  # implement this in subclasses that support this

    def do_conversion(self, migration_folder, sub_path):
        self.destination = os.path.join(self.lang_folder, migration_folder)
        convert = self.is_conversion_needed(sub_path)
        if convert:
            self.clear_results()
            file_utils.make_dir(self.destination)

            converter = None
            try:
                converter = self.init_converter(self.lang, self.repo_url, self.destination, False)
                converter.run()
                if self.not_translated(converter):
                    self.set_error("Title not converted error")
                else:
                    self.set_success(True)
                return True

            except Exception as e:
                step = "Init" if not converter else converter.trying
                msg = "Failed doing '" + step + "', error: " + str(e)
                self.set_error(msg)
        else:
            if self.last_success:
                print("\nSkipping over already converted {0} in {1}".format(self.type.upper(), self.name))
            else:
                print("\nSkipping over FAILED {0} in {1}".format(self.type.upper(), self.name))
                if self.last_error:
                    print("FAILED for: " + self.last_error + "\n")
            return True

        return False
