#/usr/bin/python3

import argparse
import json
import logging
from os import path

import paramiko
from paramiko import SSHClient
from scp import SCPClient

log = logging.getLogger('')


def exit_error(obj):
    """Function to simplify the exit with an error"""
    log.error(obj)
    exit(-1)


def src_connect(args):
    """Creates an ssh connection using the arguments provided"""
    try:
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        if args.ssh_filekey:
            key = paramiko.RSAKey.from_private_key_file(args.ssh_filekey)
            # In case you need to set an user
            if args.src_user:
                ssh.connect(args.src_address, port=args.src_port,
                            username=args.src_user, pkey=key)
            else:
                ssh.connect(args.src_address, port=args.src_port, pkey=key)
        else:
            ssh.connect(args.src_address, port=args.src_port, username=args.src_user,
                        password=args.src_passw)
        return ssh
    except Exception as e:
        # 'dict_keys' object is not subscriptable
        # It means that the connection was not successful
        log.error(e)
    return None


def create_database_backup(args, ssh):
    """Creates the mysql backup for the wordpress database"""
    pass


def download_backup(args, ssh):
    """Downloads all the backup files from the server"""
    scp = SCPClient(ssh.get_transport())
    print('Generating tar')
    stdin, stdout, stderr = ssh.exec_command('tar -cvf /tmp/wp.tar.gz {}'
                                             .format(args.src_wpath))
    status = stdout.channel.recv_exit_status()
    if status != 0:
        exit_error('Unable to create tar file (status = {})'.format(status))
    print('Downloading backup')
    try:
        scp.get('/tmp/wp.tar.gz')
    except Exception as e:
        exit_error(e)
    # It checks if the file exists
    if not path.exists('wp.tar.gz'):
        exit_error('Tar file does not exist')


def start_migration(args):
    """Handler of the different processes to complete the migration"""
    ssh = src_connect(args)
    if ssh is None:
        return
    create_database_backup(args, ssh)
    # download_backup(args, ssh)
    # stdin, stdout, stderr = ssh.exec_command('ls')
    # print(stdout.read())


def load_from_json(args):
    """Loads the arguments from a json file
    It overwrites the values read from argv
    """
    try:
        with open(args.json_file) as file:
            data = json.load(file)
        for item in dir(args):
            if item[0] == '_':
                continue
            if item in data:
                args.__setattr__(item, data[item])
    except Exception as e:
        log.error(e)


def validate_args(args):
    """Validates that the arguments object has the minimal arguments set"""
    ommited = {'json_file': True}
    ommited_debug = {}
    for item in dir(args):
        if item[0] == '_':
            continue
        if args.__getattribute__(item) is None and item not in ommited \
                and item not in ommited_debug:
            # Accepts a None ssh_filekey if the user and password are set
            if item == 'ssh_filekey' and args.src_user is not None \
                    and args.src_passw is not None:
                pass
            elif item in {'src_passw': True, 'src_user': True} \
                    and args.ssh_filekey is not None:
                pass
            else:
                print('The parameter "{}" is empty'.format(item))
                return False
    else:
        return True


def handle_options():
    """Creates the parser and adds the arguments
    Returns the arguments after being parsed from argv
    """
    parser = argparse.ArgumentParser()

    # Parameter to accept json
    parser.add_argument('-j', '--json-file', action='store',
                        help='Load the parameters from a json file')

    # Src address and credentials
    parser.add_argument('--src-address', action='store',
                        help='The address of the source machine')
    parser.add_argument('--src-port', action='store', default=22,
                        help='The port of the source machine')
    parser.add_argument('-i', '--ssh_filekey', action='store',
                        help="The ssh private key file")
    parser.add_argument('--src-user', action='store',
                        help='The username to use to connect to the source'
                             'machine')
    parser.add_argument('--src-passw', action='store',
                        help='The password to use to connect top the source'
                             'machine')

    # Wordpress info
    parser.add_argument('--src-wpath', action='store',
                        help='Set wordpress path for the source machine')

    # Database creadentials for the src
    parser.add_argument('--src-dbname', action='store',
                        help='The wordpress database name of the source machine')
    parser.add_argument('--src-dbuser', action='store', default='root',
                        help='The wordpress username for the database of the '
                             'source machine')
    parser.add_argument('--src-dbpassw', action='store',
                        help='The wordpress password for the database of the '
                             'source machine')

    args = parser.parse_args()

    # Load variables from json
    if args.json_file is not None:
        load_from_json(args)

    if validate_args(args):
        return args
    return None


def main():
    """Main function
    Sets the logger options
    Handles argument parser
    """
    sh =  logging.StreamHandler()
    fmt = '%(asctime)s - %(levelname)s - %(filename)s - %(message)s'
    sh.setFormatter(logging.Formatter(fmt))
    log.addHandler(sh)
    args = handle_options()
    log.debug(args)
    if args != None:
        start_migration(args)

if __name__ == '__main__':
    main()
