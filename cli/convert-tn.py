from __future__ import print_function, unicode_literals
import argparse
import sys
from general_tools.print_utils import print_ok
from converters.tn_converter import TNConverter

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-l', '--lang', dest='lang', default=False,
                        required=True, help='Language code of resource.')
    parser.add_argument('-r', '--gitrepo', dest='gitrepo', default=False,
                        required=True, help='Git repository where the source can be found.')
    parser.add_argument('-o', '--outdir', dest='outdir', default=False,
                        required=True, help='The output directory for markdown files.')
    parser.add_argument('-w', '--overwrite', dest='overwrite', action='store_true')
    parser.add_argument('-q', '--quiet', dest='quiet', action='store_true')
    parser.set_defaults(overwrite=False, quiet=False)

    args = parser.parse_args(sys.argv[1:])

    # do the import
    with TNConverter(args.lang, args.gitrepo, args.outdir, args.quiet, args.overwrite) as importer:
        importer.run()

    if not args.quiet:
        print_ok('ALL FINISHED: ', 'Please check the output directory.')
