from abc import ABCMeta, abstractmethod
import os.path
import re

import paramiko
from paramiko import SSHClient
from scp import SCPClient

import lib


class AbstractProcess(object):
    """Class which defines the process interface"""
    __metaclass__ = ABCMeta
    DEST = 0
    SRC = 1
    CONS = dict()

    def __init__(self):
        self.name = None
        self.target = None
        self.required = False

    @staticmethod
    def close_connections():
        for key in AbstractProcess.CONS:
            AbstractProcess.CONS[key].close()

    @abstractmethod
    def init(self):
        """Initializes the name and target"""
        pass

    @abstractmethod
    def execute(self, args, conf):
        """Implements the command to be run"""
        pass


def _ssh_connect(args, direction):
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
        lib.log.info('Connecting to %s', address)
        if fkey:
            key = paramiko.RSAKey.from_private_key_file(fkey)
            # In case you need to set an user
            if user:
                ssh.connect(address, port=port, username=user, pkey=key)
            else:
                ssh.connect(address, port=port, pkey=key)
        else:
            ssh.connect(address, port=port, username=user, password=passw)
        lib.log.info('Connection successful')
        return ssh
    except Exception as exc:
        # 'dict_keys' object is not subscriptable
        # It means that the connection was not successful
        lib.log.error('Unable to connect: ' + str(exc))
        exit(-1)
    return None


class SSHConnectSource(AbstractProcess):
    """Creates wp database dump"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Connecting to source'

    def execute(self, args, conf):
        AbstractProcess.CONS[self.target] = _ssh_connect(args, 'src')


class SSHConnectDestination(AbstractProcess):
    """Creates wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Connecting to destination'

    def execute(self, args, conf):
        AbstractProcess.CONS[self.target] = _ssh_connect(args, 'dest')


class DestCreateDBBackup(AbstractProcess):
    """Creates wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Creating wordpress tar file from destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = 'tar -cvf /tmp/wp.tar.gz {}'.format(args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestCopyWPBackup(AbstractProcess):
    """Copies the extracted files into the destination folder"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Copying source backup into destination folder'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = 'cp -r /tmp/{}/* {}/'.format(args.src_wpath, args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestCreateWPBackup(AbstractProcess):
    """Creates wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Creating database dump from destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = ('wp --allow-root --path={} db export --add-drop-table '
               '/tmp/mysql.dump'.format(args.dest_wpath))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestGetDBCredentialsProcess(AbstractProcess):
    """Saves the dest wp-config.php configuration"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Reading wp-config.php from destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = 'cat {}/wp-config.php'.format(args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))
        content = stdout.read().decode('utf-8').replace('\n', ' ')
        conf['wp-config'] = {'DB_NAME': None, 'DB_USER': None,
                             'DB_PASSWORD': None}
        simple = (".*({0})'[^']*'([^']+)"
                  .format('|'.join([key for key in conf['wp-config']])))
        match = re.match(''.join(simple for key in conf['wp-config']),
                         content)
        if match:
            items = match.groups()
            for idx in range(0, len(items), 2):
                conf['wp-config'][items[idx]] = items[idx + 1]
        for key in conf['wp-config']:
            if conf['wp-config'][key] is None:
                raise Exception('Missing field "{}" in wp-config.php in '
                                'source machine'.format(key))


class DestDecompressWordpress(AbstractProcess):
    """Decompresses wordpress tar file in destination"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Decompressing wordpress source in destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = 'tar -xvf /tmp/wp.src.tar.gz -C /tmp'
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestErasePreviousWordpress(AbstractProcess):
    """Erases wordpress folder from detsination before replacing it"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Erasing previous wordpress contents from destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = 'rm -rf {}/*'.format(args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestGetSiteUrlProcess(AbstractProcess):
    """Gets the site url using wp binary"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Get site url from destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = ('wp --allow-root --path={} option get siteurl'
               .format(args.dest_wpath))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))
        content = stdout.read().decode('utf-8').replace('\n', '')
        conf['wp-config']['DOMAIN_CURRENT_SITE'] = \
            re.sub('http(s)?://', '', content)


class DestImportDBDump(AbstractProcess):
    """Imports the dump into destination"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Importing DB dump in destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = ('wp --allow-root --path={} db import /tmp/mysql.src.dump'
               .format(args.dest_wpath))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestTruncatePosts(AbstractProcess):
    """Imports the dump into destination"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Importing DB dump in destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        tmp = conf['wp-config']
        cmd = ('tmp=($(mysql -u {0} -p{1} {2} -sNe \'show tables\' '
               '| grep post)); for table in ${{tmp[@]}}; '
               'do mysql -u {0} -p{1} {2} -e "truncate table $table"; done')
        lib.log.debug(cmd)
        cmd = (cmd.format(tmp['DB_USER'], tmp['DB_PASSWORD'], tmp['DB_NAME']))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        content = stderr.read().decode('utf-8').replace('\n', '')
        if status != 0 or 'ERROR' in content:
            raise Exception(content)


class DestReplaceConf(AbstractProcess):
    """Replaces database credentials in wp-config.php"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Replacing original database credential in wp-config.php'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        for key in conf['wp-config']:
            cmd = ("sed -i \"s/{0}'[^']*'[^']*/{0}', '{1}/g\""
                   " {2}/wp-config.php".format(key,
                                               conf['wp-config'][key],
                                               args.dest_wpath))
            lib.log.debug(cmd)
            _, stdout, _ = ssh.exec_command(cmd)
            status = stdout.channel.recv_exit_status()
            if status != 0:
                lib.log.warning('Unable to execute %s (status = %d)', cmd,
                                status)


class DestUploadDatabaseDump(AbstractProcess):
    """Uploads wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Uploading database dump to destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        scp = SCPClient(ssh.get_transport())
        scp.put('mysql.dump', '/tmp/mysql.src.dump')


class DestUploadTar(AbstractProcess):
    """Uploads wordpress tar file"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Uploading wordpress tar file dump to destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        scp = SCPClient(ssh.get_transport())
        scp.put('wp.tar.gz', '/tmp/wp.src.tar.gz')


class SrcDoDBBackup(AbstractProcess):
    """Creates the wp backup for the database"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Creating wordpress database dump from source'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = ('wp --allow-root --path={} search-replace --network --precise '
               '{} {} {} --export=/tmp/mysql.dump'
               .format(args.src_wpath,
                       conf['wp-config']['SRC_DOMAIN_CURRENT_SITE'],
                       conf['wp-config']['DOMAIN_CURRENT_SITE'],
                       ' '.join(conf['tables'])))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class SrcDoTar(AbstractProcess):
    """Creates a tar file of the wordpress path from the source"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Creating tar file'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = 'tar -cvf /tmp/wp.tar.gz {}'.format(args.src_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class SrcDownloadDBBackup(AbstractProcess):
    """Downloads the wp backup for the database"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Downloading wordpress database dump from source'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        scp = SCPClient(ssh.get_transport())
        scp.get('/tmp/mysql.dump')


class SrcDownloadTar(AbstractProcess):
    """Downloads all the backup files from the server"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Downloading tar file from source'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        scp = SCPClient(ssh.get_transport())
        scp.get('/tmp/wp.tar.gz')
        # It checks if the file exists
        if not os.path.exists('wp.tar.gz'):
            raise Exception('Tar file does not exist')


class SrcGetTableList(AbstractProcess):
    """Gathers the list of tables
    """

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Get list of tables'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = ('wp --allow-root --path={} db tables \'wp_*\' --format=csv'
               .format(args.src_wpath))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        content = stdout.read().decode('utf-8').replace('\n', '')
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))
        conf['tables'] = content.split(',')
        tmp = list()
        if args.no_users:
            for item in conf['tables']:
                if 'user' in item:
                    continue
                tmp.append(item)
            conf['tables'] = tmp


class SrcGetSiteUrlProcess(AbstractProcess):
    """Gathers the siteurl for the source machine
    The siteurl helps when it executes the search and replace in the database
    """

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Get site url from source'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = ('wp --allow-root --path={} option get siteurl'
               .format(args.src_wpath))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        content = stdout.read().decode('utf-8').replace('\n', '')
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))
        conf['wp-config']['SRC_DOMAIN_CURRENT_SITE'] = \
            re.sub('http(s)?://', '', content)
