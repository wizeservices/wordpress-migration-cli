from wordpress_migration_cli import lib
from wordpress_migration_cli.process.common import AbstractProcess

class DestDoDBBackupProcess(AbstractProcess):
    """Creates the wp backup for the database"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Creating wordpress database dump from source'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = ('wp --allow-root --path={} search-replace --network --precise '
               '{} {} {}'
               .format(args.dest_wpath,
                       conf['wp-config']['SRC_DOMAIN_CURRENT_SITE'],
                       conf['wp-config']['DOMAIN_CURRENT_SITE'],
                       ' '.join(conf['tables'])))
        lib.log.debug(cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise Exception(stderr.read().decode('utf-8'))


class DestGetTableListProcess(AbstractProcess):
    """Gathers the list of tables
    """

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Get list of tables from destination'

    def execute(self, args, conf):
        ssh = AbstractProcess.CONS[self.target]
        cmd = ('wp --allow-root --path={} db tables \'wp_*\' --format=csv'
               .format(args.dest_wpath))
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
