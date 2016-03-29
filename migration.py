import json
import os
import os.path

import process
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
        self.processes.append(process.SSHConnectSource())
        # Force to always connect to the source
        self.processes[-1].required = True
        self.processes.append(process.SSHConnectDestination())
        # Force to always connect to the destination
        self.processes[-1].required = True
        self.processes.append(process.DestGetDBCredentialsProcess())
        self.processes.append(process.DestGetSiteUrlProcess())
        self.processes.append(process.SrcGetSiteUrlProcess())
        self.processes.append(process.SrcGetTableList())
        self.processes.append(process.SrcDoDBBackup())
        self.processes.append(process.SrcDownloadDBBackup())
        self.processes.append(process.SrcDoTar())
        self.processes.append(process.SrcDownloadTar())
        self.processes.append(process.DestUploadDatabaseDump())
        self.processes.append(process.DestUploadTar())
        self.processes.append(process.DestCreateDBBackup())
        self.processes.append(process.DestCreateWPBackup())
        self.processes.append(process.DestDecompressWordpress())
        self.processes.append(process.DestErasePreviousWordpress())
        self.processes.append(process.DestCopyWPBackup())
        self.processes.append(process.DestReplaceConf())
        self.processes.append(process.DestImportDBDump())
        if self.args.no_posts:
            self.processes.append(process.DestTruncatePosts())

    def _init_processes_fix_destination(self):
        pass

    def execute(self):
        """Will loop over the list of processes to execute each of them"""

        if not self.args.no_cache and os.path.exists('.info.json'):
            with open('.info.json') as file:
                lib.log.debug('Loading json file')
                self.info = json.loads(file.read())

        tmp = [item for item in self.processes[:self.info['step']]
               if item.required]
        tmp.extend(self.processes[self.info['step']:])
        for proc in tmp:
            try:
                proc.init()
                lib.log.info('Starts "%s"', proc.name)
                proc.execute(self.args, self.info['conf'])
                self.info['step'] += 1
                with open('.info.json', 'w') as file:
                    file.write(json.dumps(self.info))
                lib.log.debug(self.info)
                lib.log.info('Done "%s"', proc.name)
            except Exception as exc:
                lib.log.error(exc)
                break
        else:
            os.remove('.info.json')
            lib.log.info('Migration complete')
        process.AbstractProcess.close_connections()
