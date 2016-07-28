
import os.path
import re

from scp import SCPClient

from wordpress_migration_cli import lib
from wordpress_migration_cli.process.common import AbstractProcess

class DestCreateDBBackupProcess(AbstractProcess):
    """Creates wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Creating wordpress tar file from destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = 'tar -cf /tmp/wp.tar.gz {}'.format(args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestCopyWPBackupProcess(AbstractProcess):
    """Copies the extracted files into the destination folder"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Copying source backup into destination folder'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        sudo = 'sudo ' if args.dest_sudo else ''
        cmd = '{}cp -r /tmp/{}/. {}/'.format(sudo,
                                             args.src_wpath,
                                             args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestCreateWPBackupProcess(AbstractProcess):
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


class DestDecompressWordpressProcess(AbstractProcess):
    """Decompresses wordpress tar file in destination"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Decompressing wordpress source in destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        sudo = 'sudo ' if args.dest_sudo else ''
        cmd = '{0}mkdir -p {1}; {0}tar -xf /tmp/wp.src.tar.gz -C {1}'.format(sudo, args.dest_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd, timeout=200)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestErasePreviousWordpressProcess(AbstractProcess):
    """Erases wordpress folder from detsination before replacing it"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Erasing previous wordpress contents from destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        sudo = 'sudo ' if args.dest_sudo else ''
        cmd = '{}rm -rf {}'.format(sudo, args.dest_wpath)
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


class DestImportDBDumpProcess(AbstractProcess):
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


class DestTruncatePostsProcess(AbstractProcess):
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


class DestUploadDatabaseDumpProcess(AbstractProcess):
    """Uploads wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Uploading database dump to destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        scp = SCPClient(ssh.get_transport(), socket_timeout=300.0)
        scp.put('mysql.dump', '/tmp/mysql.src.dump')


class DestUploadTarProcess(AbstractProcess):
    """Uploads wordpress tar file"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Uploading wordpress tar file dump to destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        scp = SCPClient(ssh.get_transport(), socket_timeout=300.0)
        scp.put('wp.tar.gz', '/tmp/wp.src.tar.gz')


class SrcCopyDestinationFileKeyProcess(AbstractProcess):
    """Upload the destination file key to the source"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Uploading destination file key to source'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        dest_filekey = '/tmp/tmp_key.pem'
        _, stdout, stderr = ssh.exec_command('rm -f {}'.format(dest_filekey))
        scp = SCPClient(ssh.get_transport(), socket_timeout=300.0)
        scp.put(args.dest_filekey, dest_filekey)
        if os.system('ssh-keygen -y -f {0} > {0}.pub'.format(args.dest_filekey)) != 0:
            raise Exception('Unable to create the key')
        ssh_dest = AbstractProcess.CONS[AbstractProcess.DEST]
        scp = SCPClient(ssh_dest.get_transport(), socket_timeout=300.0)
        pub_key = '/tmp/tmp_key.pub'
        scp.put('{}.pub'.format(args.dest_filekey), pub_key)
        key_path = '/{}/.ssh/authorized_keys' if args.dest_user == 'root' else '/home/{}/.ssh/authorized_keys'
        key_path = key_path.format(args.dest_user)
        _, stdout, stderr = ssh_dest.exec_command('grep -q "$(cat {})" {}'.format(pub_key, key_path))
        if stdout.channel.recv_exit_status() != 0:
            _, stdout, stderr = ssh_dest.exec_command('cat {} > {}'.format(pub_key, key_path))
            if stdout.channel.recv_exit_status() != 0:
                raise Exception(stderr.read())

class SrcDoDBBackupProcess(AbstractProcess):
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


class SrcDoTarProcess(AbstractProcess):
    """Creates a tar file of the wordpress path from the source"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Creating tar file'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = 'cd {}; tar -cf /tmp/wp.tar.gz .'.format(args.src_wpath)
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class SrcDownloadDBBackupProcess(AbstractProcess):
    """Downloads the wp backup for the database"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Downloading wordpress database dump from source'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        if args.fast_copy:
            cmd = 'scp -oStrictHostKeyChecking=no -P {} '.format(args.dest_port)
            dest_filekey = '/tmp/tmp_key.pem'
            if args.dest_filekey:
                cmd += '-i {} '.format(dest_filekey)

            cmd += '/tmp/mysql.dump '
            if args.dest_user:
                cmd += '{}@'.format(args.dest_user)
            cmd += '{}:/tmp/mysql.src.dump'.format(args.dest_address)
            lib.log.debug(cmd)
            _, stdout, stderr = ssh.exec_command(cmd)
            status = stdout.channel.recv_exit_status()
            if status != 0:
                raise Exception(stderr.read().decode('utf-8'))
        else:
            scp = SCPClient(ssh.get_transport(), socket_timeout=300.0)
            scp.get('/tmp/mysql.dump')


class SrcDownloadTarProcess(AbstractProcess):
    """Downloads all the backup files from the server"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Downloading tar file from source'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        if args.fast_copy:
            cmd = 'scp -oStrictHostKeyChecking=no -P {} '.format(args.dest_port)
            dest_filekey = '/tmp/tmp_key.pem'
            if args.dest_filekey:
                cmd += '-i {} '.format(dest_filekey)

            cmd += '/tmp/wp.tar.gz '
            if args.dest_user:
                cmd += '{}@'.format(args.dest_user)
            cmd += '{}:/tmp/wp.src.tar.gz'.format(args.dest_address)
            lib.log.debug(cmd)
            _, stdout, stderr = ssh.exec_command(cmd)
            status = stdout.channel.recv_exit_status()
            if status != 0:
                raise Exception(stderr.read().decode('utf-8'))
        else:
            scp = SCPClient(ssh.get_transport(), socket_timeout=300.0)
            scp.get('/tmp/wp.tar.gz')
            # It checks if the file exists
            if not os.path.exists('wp.tar.gz'):
                raise Exception('Tar file does not exist')


class SrcGetTableListProcess(AbstractProcess):
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
