Wordpress migration client
==========================
Wordpress migration client is a tool which makes easier to export a wordpress from one host to another.

### Dependencies
1. Source machine:
    1. Openssh.
    2. Tar.
    3. Wp-cli.

2. Machine in the middle (where the tool will run):
    1. Manual installation:
        1. Python 3.
        ```
        # Mac osx
        brew install python3
        ```
        2. Pip3.
        ```
        easy_install-3.5 pip
        ```
        3. Paramiko.
        ```
        pip3 install paramiko
        ```
        4. Scp.py.
        ```
        git clone https://github.com/jbardin/scp.py.git
        cd scp.py/
        python3 setup.py install
        ```

    2. Automatic installation (Mac OS X):
    ```
    sudo bash ./install_macosx.sh
    ```

3. Destination machine:
    1. Binaries:
        1. Openssh.
        2. Tar.
        3. Wp-cli.
        4. Sed.
    2. Permissions. The client needs to be filled with a user which has the proper rights over the **dest_wpath** (absolute path in the destination machine where wordpress is installed). If you decide to use root user, you need to check if root is allowed to connect by ssh, to do this do the following as root:
    ```
    # If the file does not exist, simply do
    echo PermitRootLogin yes > /etc/ssh/sshd_config

    grep PermitRootLogin /etc/ssh/sshd_config

    # If it does not print anything
    echo PermitRootLogin yes >> /etc/ssh/sshd_config

    # If it does not print "PermitRootLogin yes"
    sed -i 's/PermitRootLogin.*/PermitRootLogin yes/g' /etc/ssh/sshd_config

    # Finally restart the ssh service, for ubuntu do
    service ssh restart

    ```

### Usage
The client by default uses cache, so if it fails and you restart the client it will start where it fails. If you want to disable the cache use the **-n** flag or delete **.info.json** file.

1. Install the dependencies.
2. The tool accepts two ways to fill the parameters, directly from the console or from a json file. Also you can mix the console arguments and the json file.
3. Go to the last section of the README for the parameters reference.

#### Using a json file.
**Important**: To map console arguments to the json file you needs to erase the first two dashes and convert the middle dash to an underscore. Example: ```--src-address``` (console argument) is equivalent to ```src_address``` (json file).

1. Create a json file using the example.json template.
2. Run the following:
```
python3 main.py -j <filename>.json
```

#### Using console arguments
1. Run the following:
```
python3 main.py --src-address <ip_address> --src-port <port> ...
```

#### Mixing json file and console arguments
1. Create a json file using the example.json template. The console arguments have precedence over the json file.
2. Run the following:
```
python3 main.py -j <filename>.json --src-address <ip_address> --src-port <port> ...
```

#### Output example
Go to the following link:
https://asciinema.org/a/40740

### Architecture
![alt tag](https://raw.githubusercontent.com/wizeservices/wordpress-migration-cli/develop/docs/Architecture.png)

### Reference
```
usage: main.py [-h] [-l {debug,info,warning,error}] [-n] [-j JSON_FILE]
               [--src-address SRC_ADDRESS] [--src-port SRC_PORT]
               [--src_filekey SRC_FILEKEY] [--src-user SRC_USER]
               [--src-passw SRC_PASSW] [--src-wpath SRC_WPATH]
               [--dest-address DEST_ADDRESS] [--dest-port DEST_PORT]
               [--dest_filekey DEST_FILEKEY] [--dest-user DEST_USER]
               [--dest-passw DEST_PASSW] [--dest-wpath DEST_WPATH]

optional arguments:
  -h, --help            show this help message and exit
  -l {debug,info,warning,error}, --log-level {debug,info,warning,error}
                        Load the parameters from a json file
  -n, --no-cache        Run the client without cache
  -j JSON_FILE, --json-file JSON_FILE
                        Load the parameters from a json file
  --src-address SRC_ADDRESS
                        The address of the source machine
  --src-port SRC_PORT   The port of the source machine
  --src_filekey SRC_FILEKEY
                        The ssh private key file for the source machine
  --src-user SRC_USER   The username to use to connect to the sourcemachine
  --src-passw SRC_PASSW
                        The password to use to connect top the sourcemachine
  --src-wpath SRC_WPATH
                        Set wordpress path for the source machine
  --dest-address DEST_ADDRESS
                        The address of the destination machine
  --dest-port DEST_PORT
                        The port of the destination machine
  --dest_filekey DEST_FILEKEY
                        The ssh private key file for the destination machine
  --dest-user DEST_USER
                        The username to use to connect to the destination
                        machine
  --dest-passw DEST_PASSW
                        The password to use to connect top the destination
                        machine
  --dest-wpath DEST_WPATH
                        Set wordpress path for the destination machine
```
