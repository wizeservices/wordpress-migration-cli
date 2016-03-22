import json
import os
import os.path

import paramiko
from paramiko import SSHClient

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
        self._init_processes()

    def _init_processes(self):
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

    def execute(self):
        """Will loop over the list of processes to execute each of them"""
        self.ssh_src = self._ssh_connect('src')
        if self.ssh_src is None:
            exit(-1)

        self.ssh_dest = self._ssh_connect('dest')
        if self.ssh_dest is None:
            self.ssh_src.close()
            exit(-1)

        if not self.args.no_cache and os.path.exists('.info.json'):
            with open('.info.json') as file:
                lib.log.debug('Loading json file')
                self.info = json.loads(file.read())

        for proc in self.processes[self.info['step']:]:
            try:
                proc.init()
                tmp = (self.ssh_src
                       if proc.target == process.AbstractProcess.SRC
                       else self.ssh_dest)
                lib.log.info('Starts "%s"', proc.name)
                proc.execute(tmp, self.args, self.info['conf'])
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

        self.ssh_src.close()
        self.ssh_dest.close()

    def _ssh_connect(self, direction):
        """Creates an ssh connection using the arguments provided"""
        try:
            ssh = SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.load_system_host_keys()
            address = self.args.__getattribute__(direction + '_address')
            port = self.args.__getattribute__(direction + '_port')
            user = self.args.__getattribute__(direction + '_user')
            passw = self.args.__getattribute__(direction + '_passw')
            fkey = self.args.__getattribute__(direction + '_filekey')
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
        return None
