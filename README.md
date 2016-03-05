Wordpress migration client
==========================
Wordpress migration client is a tool which makes easier to export a wordpress from one host to another.

### Dependencies
1. Source machine:
    1. Openssh.
    2. Tar.
    3. Wp-cli.

2. Machine in the middle (where the tool will run):
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

3. Destination machine:
    1. Openssh.
    2. Tar.
    3. Wp-cli.
    4. Sed.

### Usage
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
```
18:06:32.929 - INFO - main.py - Connecting to 127.0.0.1
18:06:33.041 - INFO - main.py - Connection successful
18:06:33.041 - INFO - main.py - Saving wp-config.php configuration from destination
18:06:33.505 - INFO - main.py - wp-config.php configuration from destination saved
18:06:33.508 - INFO - main.py - Connecting to mydomain
18:06:34.137 - INFO - main.py - Connection successful
18:06:34.137 - INFO - main.py - Gathering source siteurl
18:06:34.574 - INFO - main.py - Siteurl gathered = "mydomain"
18:06:34.575 - INFO - main.py - Creating mysql source dump
18:06:35.941 - INFO - main.py - Mysql source dump done
18:06:35.941 - INFO - main.py - Downloading mysql source dump
18:06:38.692 - INFO - main.py - Mysql source dump downloaded
18:06:38.692 - INFO - main.py - Generating wordpress source tar
18:06:40.550 - INFO - main.py - Wordpress source tar generated
18:06:40.550 - INFO - main.py - Downloading source wordpress backup
18:07:05.927 - INFO - main.py - Source wordpress backup downloaded
18:07:05.930 - INFO - main.py - Connecting to 127.0.0.1
18:07:06.038 - INFO - main.py - Connection successful
18:07:06.038 - INFO - main.py - Creating destination wordpress backup
18:07:06.379 - INFO - main.py - Destination wordpress backup is done
18:07:06.379 - INFO - main.py - Creating mysql destination dump
18:07:06.456 - INFO - main.py - Mysql destination dump is done
18:07:06.456 - INFO - main.py - Uploading source backup
18:07:10.526 - INFO - main.py - Source backup uploaded
18:07:10.526 - INFO - main.py - Applying backup
18:07:13.379 - INFO - main.py - Backup complete
```

### Reference
```
usage: main.py [-h] [-l {debug,info,warning,error}] [-j JSON_FILE]
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
