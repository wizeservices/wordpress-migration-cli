#!/usr/bin/python3

"""
Dependencies:
    - Source:
        - Openssh server.
        - Tar.
        - Wp-cli.
    - Dest:
        - Wp-cli.
        - Mysqldump.
        - Sed.
"""

import argparse
import json
import logging
from os import path
import re

from scp import SCPClient
import paramiko
from paramiko import SSHClient

log = logging.getLogger('')


def exit_error(obj, ssh=None):
    """Function to simplify the exit with an error"""
    log.error(obj)
    if ssh is not None:
        ssh.close()
    exit(-1)


def ssh_connect(args, direction):
    """Creates an ssh connection using the arguments provided"""
    try:
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        address = args.__getattribute__(direction + '_address')
        port = args.__getattribute__(direction + '_port')
        user = args.__getattribute__(direction + '_user')
        passw = args.__getattribute__(direction + '_passw')
        fkey = args.__getattribute__(direction + '_filekey')
        log.info('Connecting to %s', address)
        if fkey:
            key = paramiko.RSAKey.from_private_key_file(fkey)
            # In case you need to set an user
            if user:
                ssh.connect(address, port=port, username=user, pkey=key)
            else:
                ssh.connect(address, port=port, pkey=key)
        else:
            ssh.connect(address, port=port, username=user, password=passw)
        log.info('Connection successful')
        return ssh
    except Exception as exc:
        # 'dict_keys' object is not subscriptable
        # It means that the connection was not successful
        log.error('Unable to connect: ' + str(exc))
    return None


def get_site_url_src(args, ssh):
    """Gathers the siteurl for the source machine
    The siteurl helps when it executes the search and replace in the database
    """
    try:
        cmd = ('wp --allow-root --path={} option get siteurl'
               .format(args.src_wpath))
        log.debug(cmd)
        log.info('Gathering source siteurl')
        _, stdout, stderr = ssh.exec_command(cmd)
        content = stdout.read().decode('utf-8').replace('\n', '')
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)
        result = re.sub('http(s)?://', '', content)
        log.info('Siteurl gathered = "%s"', result)
        return result
    except Exception as exc:
        exit_error(exc, ssh)


def get_conf_from_wp_config_dest(args, ssh):
    """Saves the dest wp-config.php configuration"""
    try:
        log.info('Saving wp-config.php configuration from destination')
        cmd = 'cat {}/wp-config.php'.format(args.dest_wpath)
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)
        content = stdout.read().decode('utf-8').replace('\n', ' ')
        required = {'DB_NAME': None, 'DB_USER': None, 'DB_PASSWORD': None}
        simple = (".*({0})'[^']*'([^']+)"
                  .format('|'.join([key for key in required])))
        match = re.match(''.join(simple for key in required), content)
        if match:
            items = match.groups()
            for idx in range(0, len(items), 2):
                required[items[idx]] = items[idx + 1]
        required['DOMAIN_CURRENT_SITE'] = None
        # Also gets the site url using wp binary
        cmd = ('wp --allow-root --path={} option get siteurl'
               .format(args.dest_wpath))
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)
        content = stdout.read().decode('utf-8').replace('\n', '')
        required['DOMAIN_CURRENT_SITE'] = re.sub('http(s)?://', '', content)
        for key in required:
            if required[key] is None:
                exit_error('Missing field "{}" in wp-config.php in source '
                           'machine'.format(key), ssh)
        log.info('wp-config.php configuration from destination saved')
        return required
    except Exception as exc:
        exit_error(exc, ssh)


def create_database_backup(args, ssh, conf):
    """Creates the mysql backup for the wordpress database"""
    try:
        log.info('Creating mysql source dump')
        cmd = ('wp --allow-root --path={} search-replace --network --precise '
               '--all-tables {} {} --export=/tmp/mysql.dump'
               .format(args.src_wpath,
                       conf['SRC_DOMAIN_CURRENT_SITE'],
                       conf['DOMAIN_CURRENT_SITE']))
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)
        log.info('Mysql source dump done')
        scp = SCPClient(ssh.get_transport())
        log.info('Downloading mysql source dump')
        scp.get('/tmp/mysql.dump')
        log.info('Mysql source dump downloaded')
        # It no longer needs this value
        del conf['SRC_DOMAIN_CURRENT_SITE']
    except Exception as exc:
        exit_error(exc, ssh)


def download_backup(args, ssh):
    """Downloads all the backup files from the server"""
    try:
        scp = SCPClient(ssh.get_transport())
        log.info('Generating wordpress source tar')
        cmd = 'tar -cvf /tmp/wp.tar.gz {}'.format(args.src_wpath)
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)
        log.info('Wordpress source tar generated')
        log.info('Downloading source wordpress backup')
        scp.get('/tmp/wp.tar.gz')
        # It checks if the file exists
        if not path.exists('wp.tar.gz'):
            exit_error('Tar file does not exist', ssh)
        log.info('Source wordpress backup downloaded')
    except Exception as exc:
        exit_error(exc, ssh)


def upload_backup(ssh):
    """Uploads the mysql dump and the wordpress folder to source machine"""
    try:
        scp = SCPClient(ssh.get_transport())
        log.info('Uploading source backup')
        scp.put('wp.tar.gz', '/tmp/wp.src.tar.gz')
        scp.put('mysql.dump', '/tmp/mysql.src.dump')
        log.info('Source backup uploaded')
    except Exception as exc:
        exit_error(exc, ssh)


def save_old_wordpress(args, ssh):
    """Backups the destination database and wordpress installation
    It helps if the user manually wants to restore it previous installation
    """
    try:
        log.info('Creating destination wordpress backup')
        cmd = 'tar -cvf /tmp/wp.tar.gz {}'.format(args.dest_wpath)
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)
        log.info('Destination wordpress backup is done')
        log.info('Creating mysql destination dump')
        cmd = ('mysqldump --add-drop-table -u {} -p{} {} > /tmp/mysql.dump'
               .format(args.dest_dbuser, args.dest_dbpassw, args.dest_dbname))
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)
        log.info('Mysql destination dump is done')
    except Exception as exc:
        exit_error(exc, ssh)


def apply_backup(args, ssh, conf):
    """It executes the steps needed to import the wordpress installation
    Decompress wordpress installation
    Deletes previous wordpress installation
    Imports the database
    Modifies the wp-config.php to set the dbname, dbuser, dbpassword and
        siteurl
    """
    try:
        log.info('Applying backup')
        cmd = 'tar -xvf /tmp/wp.src.tar.gz -C /tmp'
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)

        # It will erase only the content, and preserve it as an empty folder
        cmd = 'rm -rf {}/*'.format(args.dest_wpath)
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)

        # Then it copies the uncompressed folder to the wordpress dest folder
        cmd = 'cp -r /tmp/{}/* {}/'.format(args.src_wpath, args.dest_wpath)
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)

        # Then it applies the mysql backup
        cmd = ('mysql -u {} -p{} {} < /tmp/mysql.src.dump'
               .format(args.dest_dbuser, args.dest_dbpassw, args.dest_dbname))
        log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            exit_error(stderr.read().decode('utf-8'), ssh)

        # Finally it replaces the conf values in wp-config.php
        for key in conf:
            cmd = ("sed -i \"s/{0}'[^']*'[^']*/{0}', '{1}/g\""
                   " {2}/wp-config.php".format(key,
                                               conf[key],
                                               args.dest_wpath))
            log.debug(cmd)
            _, stdout, stderr = ssh.exec_command(cmd)
            status = stdout.channel.recv_exit_status()
            if status != 0:
                log.warning('Unable to execute %s (status = %d)', cmd, status)
        log.info('Backup complete')
    except Exception as exc:
        exit_error(exc, ssh)


def start_migration(args):
    """Handler of the different processes to complete the migration"""
    conf = dict()
    # First it needs some information to replace it on the dump
    ssh = ssh_connect(args, 'dest')
    if ssh is None:
        return

    # Read dest wp-config.php
    conf.update(get_conf_from_wp_config_dest(args, ssh))
    ssh.close()

    # Connects to the source machine
    ssh = ssh_connect(args, 'src')
    if ssh is None:
        return

    # It needs the src site url to replace the value on the database
    conf['SRC_DOMAIN_CURRENT_SITE'] = get_site_url_src(args, ssh)
    create_database_backup(args, ssh, conf)
    download_backup(args, ssh)
    ssh.close()

    # Connects to the destination machine
    ssh = ssh_connect(args, 'dest')
    if ssh is None:
        return

    # Backups destination wordpress installation
    save_old_wordpress(args, ssh)
    # Uploads to destination machine the source wordpress installation
    upload_backup(ssh)
    apply_backup(args, ssh, conf)

    # Finally closes the connections if everything was ok
    ssh.close()


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
    except Exception as exc:
        log.error(exc)


def handle_options():
    """Creates the parser and adds the arguments
    Returns the arguments after being parsed from argv
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', action='store',
                        choices=['debug', 'info', 'warning', 'error'],
                        default='info',
                        help='Load the parameters from a json file')

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

    # Database creadentials for the src
    parser.add_argument('--src-dbname', action='store',
                        help='The wordpress database name of the source '
                             'machine')
    parser.add_argument('--src-dbuser', action='store', default='root',
                        help='The wordpress username for the database of the '
                             'source machine')
    parser.add_argument('--src-dbpassw', action='store',
                        help='The wordpress password for the database of the '
                             'source machine')

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

    # Database creadentials for the dest
    parser.add_argument('--dest-dbname', action='store',
                        help='The wordpress database name of the destination'
                             'machine')
    parser.add_argument('--dest-dbuser', action='store', default='root',
                        help='The wordpress username for the database of the '
                             'destination machine')
    parser.add_argument('--dest-dbpassw', action='store',
                        help='The wordpress password for the database of the '
                             'destination machine')

    args = parser.parse_args()

    # Load variables from json
    if args.json_file is not None:
        load_from_json(args)

    return args


def main():
    """Main function
    Sets the logger options
    Handles argument parser
    """
    shr = logging.StreamHandler()
    fmt = '%(asctime)s.%(msecs)03d - %(levelname)s - %(filename)s - %(message)s'
    shr.setFormatter(logging.Formatter(fmt, "%H:%M:%S"))
    log.addHandler(shr)
    args = handle_options()
    levels = {'debug': logging.DEBUG, 'info': logging.INFO,
              'warning': logging.WARNING, 'error': logging.ERROR}
    log.setLevel(levels[args.log_level])
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    del levels
    log.debug(args)
    if args is not None:
        start_migration(args)

if __name__ == '__main__':
    main()
