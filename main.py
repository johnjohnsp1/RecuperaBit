#!/usr/bin/env python
"""Main RecuperaBit process."""

# RecuperaBit
# Copyright 2014-2016 Andrea Lazzarotto
#
# This file is part of RecuperaBit.
#
# RecuperaBit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RecuperaBit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RecuperaBit. If not, see <http://www.gnu.org/licenses/>.


import sys
import logging
import argparse
import pickle
import itertools
import locale
import codecs
import os.path

from recuperabit import utils
from recuperabit import logic
# scanners
from recuperabit.fs.ntfs import NTFSScanner

__author__ = "Andrea Lazzarotto"
__copyright__ = "Copyright 2014-2016, Andrea Lazzarotto"
__license__ = "GPLv3"
__version__ = "1.0"
__maintainer__ = "Andrea Lazzarotto"
__email__ = "andrea.lazzarotto@gmail.com"


"""Wrapping sys.stdout into an instance of StreamWriter will allow writing
unicode data with sys.stdout.write() and print.
https://wiki.python.org/moin/PrintFails"""
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
sys.stderr = codecs.getwriter(locale.getpreferredencoding())(sys.stderr)

# classes of available scanners
plugins = (
    NTFSScanner,
)

commands = (
    ('help', 'Print this help message'),
    ('recoverable', 'List recoverable partitions'),
    ('other', 'List unrecoverable partitions'),
    ('allparts', 'List all partitions'),
    ('tree <part#>', 'Show contents of partition (tree)'),
    ('csv <part#> <path>', 'Save a CSV representation in a file'),
    ('bodyfile <part#> <path>', 'Save a body file representation in a file'),
    ('tikzplot <part#> [<path>]', 'Produce LaTeX code to draw a Tikz figure'),
    ('restore <part#> <file>', 'Recursively restore files from <file>'),
    ('quit', 'Close the program')
)

rebuilt = set()


def list_parts(parts, shorthands, test):
    """List partitions corresponding to test."""
    for i, part in shorthands:
        if test(parts[part]):
            print 'Partition #' + str(i), '->', parts[part]


def check_valid_part(num, parts, shorthands):
    """Check if the required partition is valid."""
    try:
        i = int(num)
    except ValueError:
        print 'Value is not valid!'
        return None
    if i in xrange(len(shorthands)):
        i, par = shorthands[i]
        part = parts[par]
        if par not in rebuilt:
            print 'Rebuilding partition...'
            part.rebuild()
            rebuilt.add(par)
            print 'Done'
        return part
    print 'No partition with given ID!'
    return None


def interpret(cmd, arguments, parts, shorthands, outdir):
    """Perform command required by user."""
    if cmd == 'help':
        print 'Available commands:'
        for name, desc in commands:
            print '    %s%s' % (name.ljust(28), desc)
    elif cmd == 'tree':
        if len(arguments) != 1:
            print 'Wrong number of parameters!'
        else:
            part = check_valid_part(arguments[0], parts, shorthands)
            if part is not None:
                print '-'*10
                print utils.tree_folder(part.root)
                print utils.tree_folder(part.lost)
                print '-'*10
    elif cmd == 'bodyfile':
        if len(arguments) != 2:
            print 'Wrong number of parameters!'
        else:
            part = check_valid_part(arguments[0], parts, shorthands)
            if part is not None:
                contents = [
                    '# ---' + repr(part) + '---',
                    '# Full paths'
                ] + utils.bodyfile_folder(part.root) + [
                    '# \n# Orphaned files'
                ] + utils.bodyfile_folder(part.lost)
                fname = os.path.join(outdir, arguments[1])
                try:
                    with codecs.open(fname, 'w', encoding='utf8') as outfile:
                        outfile.write('\n'.join(contents))
                        print 'Saved body file to %s' % fname
                except IOError:
                    print 'Cannot open file %s for output!' % fname
    elif cmd == 'csv':
        if len(arguments) != 2:
            print 'Wrong number of parameters!'
        else:
            part = check_valid_part(arguments[0], parts, shorthands)
            if part is not None:
                contents = utils.csv_part(part)
                fname = os.path.join(outdir, arguments[1])
                try:
                    with codecs.open(fname, 'w', encoding='utf8') as outfile:
                        outfile.write(
                            '\n'.join(contents)
                        )
                        print 'Saved CSV file to %s' % fname
                except IOError:
                    print 'Cannot open file %s for output!' % fname
    elif cmd == 'tikzplot':
        if len(arguments) not in (1, 2):
            print 'Wrong number of parameters!'
        else:
            part = check_valid_part(arguments[0], parts, shorthands)
            if part is not None:
                if len(arguments) > 1:
                    fname = os.path.join(outdir, arguments[1])
                    try:
                        with codecs.open(fname, 'w') as outfile:
                            outfile.write(utils.tikz_part(part) + '\n')
                            print 'Saved Tikz code to %s' % fname
                    except IOError:
                        print 'Cannot open file %s for output!' % fname
                else:
                    print utils.tikz_part(part)
    elif cmd == 'restore':
        if len(arguments) != 2:
            print 'Wrong number of parameters!'
        else:
            partid = arguments[0]
            part = check_valid_part(partid, parts, shorthands)
            if part is not None:
                index = arguments[1]
                partition_dir = os.path.join(outdir, 'Partition' + str(partid))
                myfile = None
                try:
                    indexi = int(index)
                except ValueError:
                    indexi = index
                for i in [index, indexi]:
                    myfile = part.get(i, myfile)
                if myfile is None:
                    print 'The index is not valid'
                else:
                    logic.recursive_restore(myfile, part, partition_dir)

    elif cmd == 'recoverable':
        list_parts(parts, shorthands, lambda x: x.recoverable)
    elif cmd == 'other':
        list_parts(parts, shorthands, lambda x: not x.recoverable)
    elif cmd == 'allparts':
        list_parts(parts, shorthands, lambda x: True)
    elif cmd == 'quit':
        exit(0)
    else:
        print 'Unknown command.'


def main():
    """Wrap the program logic inside a function."""
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    print 'RecuperaBit', __version__
    print __copyright__, '<%s>' % __email__
    print 'Released under the', __license__
    print ''

    parser = argparse.ArgumentParser(
        description='Reconstruct the directory structure of possibly damaged '
                    'filesystems.'
    )
    parser.add_argument('path', type=str, help='path to the disk image')
    parser.add_argument(
        '-s', '--savefile', type=str, help='path of the scan save file'
    )
    parser.add_argument(
        '-w', '--overwrite', action='store_true',
        help='force overwrite of the save file'
    )
    parser.add_argument(
        '-o', '--outputdir', type=str, help='directory for restored contents'
        ' and output files'
    )
    args = parser.parse_args()

    try:
        image = open(args.path, 'rb')
    except IOError:
        logging.error('Unable to open image file!')
        exit(1)

    read_results = False
    write_results = False

    # Set output directory
    if args.outputdir is None:
        logging.info('No output directory specified, defaulting to '
                     'recuperabit_output')
        args.outputdir = 'recuperabit_output'

    # Try to reload information from the savefile
    if args.savefile is not None:
        if args.overwrite:
            logging.info('Results will be saved to %s', args.savefile)
            write_results = True
        else:
            logging.info('Checking if results already exist.')
            try:
                savefile = open(args.savefile, 'rb')
                logging.info('Results will be read from %s', args.savefile)
                read_results = True
            except IOError:
                logging.info('Unable to open save file.')
                logging.info('Results will be saved to %s', args.savefile)
                write_results = True

    if read_results:
        logging.info('The save file exists. Trying to read it...')
        try:
            indexes = pickle.load(savefile)
        except IndexError:
            logging.error('Malformed save file!')
            exit(1)
    else:
        indexes = itertools.count()

    # Ask for confirmation before beginning the process
    try:
        confirm = raw_input('Type [Enter] to start the analysis or '
                            '"exit" / "quit" / "q" to quit: ')
    except EOFError:
        print ''
        exit(0)
    if confirm in ('exit', 'quit', 'q'):
        exit(0)

    scanners = [pl(image) for pl in plugins]

    interesting = utils.feed_all(image, scanners, indexes)

    logging.info('First scan completed')

    if write_results:
        logging.info('Saving results to %s', args.savefile)
        savefile = open(args.savefile, 'wb')
        pickle.dump(interesting, savefile)

    # Ask for partitions
    parts = {}
    for scanner in scanners:
        parts.update(scanner.get_partitions())

    shorthands = list(enumerate(parts))

    logging.info('%i partitions found.', len(parts))
    while True:
        print '\nWrite command ("help" for details):'
        print '>',
        try:
            command = raw_input().strip().split(' ')
        except EOFError:
            print ''
            exit(0)
        cmd = command[0]
        arguments = command[1:]
        interpret(cmd, arguments, parts, shorthands, args.outputdir)

if __name__ == '__main__':
    main()
