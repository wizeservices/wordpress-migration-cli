import json
import os
import os.path

import process.common
import process.all
import process.fix
import lib


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
        self.processes.append(process.common.SSHConnectSourceProcess())
        # Force to always connect to the source
        self.processes[-1].required = True
        self.processes.append(process.common.SSHConnectDestinationProcess())
        # Force to always connect to the destination
        self.processes[-1].required = True
        self.processes.append(process.all.DestGetDBCredentialsProcess())
        self.processes.append(process.all.DestGetSiteUrlProcess())
        self.processes.append(process.all.SrcGetSiteUrlProcess())
        self.processes.append(process.all.SrcGetTableListProcess())
        self.processes.append(process.all.SrcDoDBBackupProcess())
        self.processes.append(process.all.SrcDownloadDBBackupProcess())
        self.processes.append(process.all.SrcDoTarProcess())
        self.processes.append(process.all.SrcDownloadTarProcess())
        self.processes.append(process.all.DestUploadDatabaseDumpProcess())
        self.processes.append(process.all.DestUploadTarProcess())
        self.processes.append(process.all.DestCreateDBBackupProcess())
        self.processes.append(process.all.DestCreateWPBackupProcess())
        self.processes.append(process.all.DestDecompressWordpressProcess())
        self.processes.append(process.all.DestErasePreviousWordpressProcess())
        self.processes.append(process.all.DestCopyWPBackupProcess())
        self.processes.append(process.common.DestReplaceConfProcess())
        self.processes.append(process.all.DestImportDBDumpProcess())
        if self.args.no_posts:
            self.processes.append(process.all.DestTruncatePostsProcess())

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
        self.processes.append(process.common.SSHConnectDestinationProcess())
        # Force to always connect to the destination
        self.processes[-1].required = True
        self.processes.append(process.fix.DestGetTableListProcess())
        self.processes.append(process.fix.DestDoDBBackupProcess())
        self.processes.append(process.common.DestReplaceConfProcess())

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
        tmp.extend(self.processes[self.info['step']:])
        for proc in tmp:
            try:
                proc.init()
                lib.log.info('Starts "%s"', proc.name)
                proc.execute(self.args, self.info['conf'])
                lib.log.info('Done "%s"', proc.name)
                self.info['step'] += 1
                with open('.info.json', 'w') as file:
                    file.write(json.dumps(self.info))
                lib.log.debug(self.info)
            except Exception as exc:
                lib.log.error(exc)
                break
        else:
            os.remove('.info.json')
            lib.log.info('Migration complete')
        process.common.AbstractProcess.close_connections()
