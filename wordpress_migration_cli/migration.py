import json
import os
import os.path

from wordpress_migration_cli.process import common
from wordpress_migration_cli.process import all
from wordpress_migration_cli.process import fix
from wordpress_migration_cli import lib


class Migration(object):
    """Migration class handler"""

    def __init__(self, args):
        self.args = args
        self.info = {'step': 0, 'conf': dict()}
        self.ssh_src = None
        self.ssh_dest = None
        self.processes = list()
        if self.args.fix_destination_hostname:
            self._init_processes_fix_destination()
        else:
            self._init_processes_normal()

    def _init_processes_normal(self):
        self.info['type'] = 'all'
        self.processes.append(common.SSHConnectSourceProcess())
        # Force to always connect to the source
        self.processes[-1].required = True
        self.processes.append(common.SSHConnectDestinationProcess())
        # Force to always connect to the destination
        self.processes[-1].required = True
        self.processes.append(all.DestGetDBCredentialsProcess())
        self.processes.append(all.DestGetSiteUrlProcess())
        self.processes.append(all.SrcGetSiteUrlProcess())
        self.processes.append(all.SrcGetTableListProcess())
        self.processes.append(all.SrcDoDBBackupProcess())
        self.processes.append(all.SrcDoTarProcess())
        if self.args.fast_copy:
            if self.args.dest_filekey:
                # It needs to upload only if the destination has a filekey
                self.processes.append(all.SrcCopyDestinationFileKeyProcess())
            self.processes.append(all.SrcDownloadDBBackupProcess())
            self.processes.append(all.SrcDownloadTarProcess())
        else:
            # If the user selected fast copy, the tool won't need to upload
            # anything, because the backup is transferred directly from source
            # to destination
            self.processes.append(all.SrcDownloadDBBackupProcess())
            self.processes.append(all.SrcDownloadTarProcess())
            self.processes.append(all.DestUploadDatabaseDumpProcess())
            self.processes.append(all.DestUploadTarProcess())
        self.processes.append(all.DestCreateDBBackupProcess())
        self.processes.append(all.DestCreateWPBackupProcess())
        self.processes.append(all.DestErasePreviousWordpressProcess())
        self.processes.append(all.DestDecompressWordpressProcess())
        self.processes.append(common.DestReplaceConfProcess())
        self.processes.append(all.DestImportDBDumpProcess())
        if self.args.no_posts:
            self.processes.append(all.DestTruncatePostsProcess())

    def _init_processes_fix_destination(self):
        if self.args.current_site is None or self.args.current_site == '':
            lib.log.error('Missing current site')
            exit(-1)
        if self.args.new_site is None or self.args.new_site == '':
            lib.log.error('Missing new site')
            exit(-1)
        self.info['conf']['wp-config'] = \
            {'DOMAIN_CURRENT_SITE': self.args.new_site,
             'SRC_DOMAIN_CURRENT_SITE': self.args.current_site}
        self.info['type'] = 'fix'
        self.processes.append(common.SSHConnectDestinationProcess())
        # Force to always connect to the destination
        self.processes[-1].required = True
        self.processes.append(fix.DestGetTableListProcess())
        self.processes.append(fix.DestDoDBBackupProcess())
        self.processes.append(common.DestReplaceConfProcess())

    def execute(self):
        """Will loop over the list of processes to execute each of them"""
        tmp_info = None
        if not self.args.no_cache and os.path.exists('.info.json'):
            with open('.info.json') as file:
                lib.log.debug('Loading json file')
                tmp_info = json.loads(file.read())

        if tmp_info and ((self.args.fix_destination_hostname and
             tmp_info['type'] == 'fix') or
            (not self.args.fix_destination_hostname and
             tmp_info['type'] == 'all')):
            self.info = tmp_info

        tmp = [item for item in self.processes[:self.info['step']]
               if item.required]
        omit_count = len(tmp)
        tmp.extend(self.processes[self.info['step']:])
        self.info['process_list'] = {idx:str(item) for idx, item in enumerate(self.processes)}
        index = 0
        for proc in tmp:
            try:
                proc.init()
                lib.log.info('Starts "%s"', proc.name)
                proc.execute(self.args, self.info['conf'])
                lib.log.info('Done "%s"', proc.name)
                # It does not add another step when doing a required step
                # from the second run
                if index >= omit_count:
                    self.info['step'] += 1
                index += 1
                with open('.info.json', 'w') as file:
                    file.write(json.dumps(self.info, indent=2, sort_keys=True))
                lib.log.debug(self.info)
            except Exception as exc:
                lib.log.error(exc)
                break
        else:
            os.remove('.info.json')
            lib.log.info('Migration complete')
        common.AbstractProcess.close_connections()
