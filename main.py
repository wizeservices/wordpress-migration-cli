#!/usr/bin/python3

import argparse
import json
import logging

from migration import Migration
import lib


def load_from_json(args, defaults):
    """Loads the arguments from a json file
    It overwrites the values read from argv
    """
    try:
        with open(args.json_file) as file:
            data = json.load(file)
        for item in dir(args):
            if item[0] == '_':
                continue
            if item in data and \
                    args.__getattribute__(item) == defaults.get(item, None):
                args.__setattr__(item, data[item])
    except Exception as exc:
        lib.log.error(exc)


def handle_options():
    """Creates the parser and adds the arguments
    Returns the arguments after being parsed from argv
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', action='store',
                        choices=['debug', 'info', 'warning', 'error'],
                        default='info',
                        help='Change the log level')

    parser.add_argument('-n', '--no-cache', action='store_true',
                        help='Run the client without cache')

    parser.add_argument('--no-users', action='store_true',
                        help='Omit users in migration')
    parser.add_argument('--no-posts', action='store_true',
                        help='Omit posts in migration')

    # Parameter to accept json
    parser.add_argument('-j', '--json-file', action='store',
                        help='Load the parameters from a json file')

    # Src address and credentials
    parser.add_argument('--src-address', action='store',
                        help='The address of the source machine')
    parser.add_argument('--src-port', action='store', default=22,
                        help='The port of the source machine')
    parser.add_argument('--src_filekey', action='store',
                        help='The ssh private key file for the source machine')
    parser.add_argument('--src-user', action='store',
                        help='The username to use to connect to the source'
                             'machine')
    parser.add_argument('--src-passw', action='store',
                        help='The password to use to connect top the source'
                             'machine')

    # Wordpress info for src
    parser.add_argument('--src-wpath', action='store',
                        help='Set wordpress path for the source machine')

    # Dest address and credentials
    parser.add_argument('--dest-address', action='store',
                        help='The address of the destination machine')
    parser.add_argument('--dest-port', action='store', default=22,
                        help='The port of the destination machine')
    parser.add_argument('--dest_filekey', action='store',
                        help='The ssh private key file for the destination '
                             'machine')
    parser.add_argument('--dest-user', action='store',
                        help='The username to use to connect to the '
                             'destination machine')
    parser.add_argument('--dest-passw', action='store',
                        help='The password to use to connect top the '
                             'destination machine')

    # Wordpress info for dest
    parser.add_argument('--dest-wpath', action='store',
                        help='Set wordpress path for the destination machine')

    args = parser.parse_args()
    defaults = {item.dest: item.default
                for item in parser._get_optional_actions()
                if item.default is not None}

    # Load variables from json
    if args.json_file is not None:
        load_from_json(args, defaults)

    return args


def main():
    """Main function
    Sets the logger options
    Handles argument parser
    """
    shr = logging.StreamHandler()
    fmt = ('%(asctime)s.%(msecs)03d - %(levelname)s - %(filename)s - '
           '%(message)s')
    shr.setFormatter(logging.Formatter(fmt, "%H:%M:%S"))
    lib.log.addHandler(shr)
    args = handle_options()
    levels = {'debug': logging.DEBUG, 'info': logging.INFO,
              'warning': logging.WARNING, 'error': logging.ERROR}
    lib.log.setLevel(levels[args.log_level])
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    del levels
    lib.log.debug(args)
    if args is not None:
        Migration(args).execute()

if __name__ == '__main__':
    main()
