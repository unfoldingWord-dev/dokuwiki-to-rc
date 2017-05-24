from __future__ import print_function, unicode_literals
import argparse
import sys
from general_tools.print_utils import print_ok
from converters.tn_converter import TNConverter

if __name__ == '__main__':
    print()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-l', '--lang', dest='lang', default=False,
                        required=True, help='Language code of resource.')
    parser.add_argument('-r', '--gitrepo', dest='gitrepo', default=False,
                        required=True, help='Git repository where the source can be found.')
    parser.add_argument('-o', '--outdir', dest='out_dir', default=False,
                        required=True, help='The output directory for Bible tN markdown files.')

    args = parser.parse_args(sys.argv[1:])

    # do the import
    with TNConverter(args.lang, args.gitrepo, args.out_dir, False) as importer:
        importer.run()

    print_ok('ALL FINISHED: ', 'Please check the output directory.')
