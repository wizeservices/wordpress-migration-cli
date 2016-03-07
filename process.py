from abc import ABCMeta, abstractmethod
import os.path
import re

from scp import SCPClient

import lib


class AbstractProcess(object):
    """Class which defines the process interface"""
    __metaclass__ = ABCMeta
    DEST = 0
    SRC = 1

    def __init__(self):
        self.name = None
        self.target = None

    @abstractmethod
    def init(self):
        """Initializes the name and target"""
        pass

    @abstractmethod
    def execute(self, ssh, args, conf):
        """Implements the command to be run"""
        pass


class DestCreateDBBackup(AbstractProcess):
    """Creates wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Creating database dump from destination'

    def execute(self, ssh, args, conf):
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

    def execute(self, ssh, args, conf):
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
        self.name = 'Creating wordpress tar file from destination'

    def execute(self, ssh, args, conf):
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

    def execute(self, ssh, args, conf):
        cmd = 'cat {}/wp-config.php'.format(args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))
        content = stdout.read().decode('utf-8').replace('\n', ' ')
        conf.update({'DB_NAME': None, 'DB_USER': None, 'DB_PASSWORD': None})
        simple = (".*({0})'[^']*'([^']+)"
                  .format('|'.join([key for key in conf])))
        match = re.match(''.join(simple for key in conf), content)
        if match:
            items = match.groups()
            for idx in range(0, len(items), 2):
                conf[items[idx]] = items[idx + 1]
        for key in conf:
            if conf[key] is None:
                raise Exception('Missing field "{}" in wp-config.php in '
                                'source machine'.format(key))


class DestDecompressWordpress(AbstractProcess):
    """Decompresses wordpress tar file in destination"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Decompressing wordpress source in destination'

    def execute(self, ssh, args, conf):
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

    def execute(self, ssh, args, conf):
        cmd = 'rm -rf {}/*'.format(args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestImportDBdump(AbstractProcess):
    """Imports the dump into destination"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Importing DB dump in destination'

    def execute(self, ssh, args, conf):

        cmd = ('wp --allow-root --path={} db import /tmp/mysql.src.dump'
               .format(args.dest_wpath))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestReplaceConf(AbstractProcess):
    """Replaces database credentials in wp-config.php"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Replacing original database creadential in wp-config.php'

    def execute(self, ssh, args, conf):
        for key in conf:
            cmd = ("sed -i \"s/{0}'[^']*'[^']*/{0}', '{1}/g\""
                   " {2}/wp-config.php".format(key,
                                               conf[key],
                                               args.dest_wpath))
            lib.log.debug(cmd)
            _, stdout, _ = ssh.exec_command(cmd)
            status = stdout.channel.recv_exit_status()
            if status != 0:
                lib.log.warning('Unable to execute %s (status = %d)', cmd,
                                status)


class DestGetSiteUrlProcess(AbstractProcess):
    """Gets the site url using wp binary"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Get site url from destination'

    def execute(self, ssh, args, conf):
        cmd = ('wp --allow-root --path={} option get siteurl'
               .format(args.dest_wpath))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))
        content = stdout.read().decode('utf-8').replace('\n', '')
        conf['DOMAIN_CURRENT_SITE'] = re.sub('http(s)?://', '', content)


class DestUploadDatabaseDump(AbstractProcess):
    """Uploads wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Uploading database dump to destination'

    def execute(self, ssh, args, conf):
        scp = SCPClient(ssh.get_transport())
        scp.put('mysql.dump', '/tmp/mysql.src.dump')


class DestUploadTar(AbstractProcess):
    """Uploads wordpress tar file"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Uploading wordpress tar file dump to destination'

    def execute(self, ssh, args, conf):
        scp = SCPClient(ssh.get_transport())
        scp.put('wp.tar.gz', '/tmp/wp.src.tar.gz')


class SrcDoDBBackup(AbstractProcess):
    """Creates the wp backup for the database"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Creating wordpress database dump from source'

    def execute(self, ssh, args, conf):
        cmd = ('wp --allow-root --path={} search-replace --network --precise '
               '--all-tables {} {} --export=/tmp/mysql.dump'
               .format(args.src_wpath,
                       conf['SRC_DOMAIN_CURRENT_SITE'],
                       conf['DOMAIN_CURRENT_SITE']))
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

    def execute(self, ssh, args, conf):
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

    def execute(self, ssh, args, conf):
        scp = SCPClient(ssh.get_transport())
        scp.get('/tmp/mysql.dump')


class SrcDownloadTar(AbstractProcess):
    """Downloads all the backup files from the server"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Downloading tar file from source'

    def execute(self, ssh, args, conf):
        scp = SCPClient(ssh.get_transport())
        scp.get('/tmp/wp.tar.gz')
        # It checks if the file exists
        if not os.path.exists('wp.tar.gz'):
            raise Exception('Tar file does not exist')


class SrcGetSiteUrlProcess(AbstractProcess):
    """Gathers the siteurl for the source machine
    The siteurl helps when it executes the search and replace in the database
    """

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Get site url from source'

    def execute(self, ssh, args, conf):
        cmd = ('wp --allow-root --path={} option get siteurl'
               .format(args.src_wpath))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        content = stdout.read().decode('utf-8').replace('\n', '')
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))
        conf['SRC_DOMAIN_CURRENT_SITE'] = re.sub('http(s)?://', '', content)