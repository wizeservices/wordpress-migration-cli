from abc import ABCMeta, abstractmethod

import paramiko
from paramiko import SSHClient

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


class SSHConnectSourceProcess(AbstractProcess):
    """Creates wp database dump"""

    def init(self):
        self.target = AbstractProcess.SRC
        self.name = 'Connecting to source'

    def execute(self, args, conf):
        AbstractProcess.CONS[self.target] = _ssh_connect(args, 'src')


class SSHConnectDestinationProcess(AbstractProcess):
    """Creates wp database dump"""

    def init(self):
        self.target = AbstractProcess.DEST
        self.name = 'Connecting to destination'

    def execute(self, args, conf):
        AbstractProcess.CONS[self.target] = _ssh_connect(args, 'dest')


class DestReplaceConfProcess(AbstractProcess):
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
