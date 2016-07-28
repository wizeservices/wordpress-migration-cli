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

        3. Python dependencies.
          ```
        pip3 install -r requirements.txt
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
##### Complete Migration Result
[![asciicast](https://asciinema.org/a/40740.png)](https://asciinema.org/a/40740)

##### Fix Destination Hostname Feature
[![asciicast](https://asciinema.org/a/1ah6seolg5jipt98o75wca4wm.png)](https://asciinema.org/a/1ah6seolg5jipt98o75wca4wm)

### Architecture
![alt tag](https://raw.githubusercontent.com/wizeservices/wordpress-migration-cli/develop/docs/Architecture.png)


###Scenarios
####Source and destination machine
All the scenarios below can be mixed, for instance ```python3 main.py -j file.json --dest-sudo --no-users --no-posts --fast-copy```. The json file used in the scenarios below is the following:
```
{
    "src_address": "127.0.0.1",
    "src_user": "vagrant",
    "src_passw": "vagrant",
    "src_wpath": "/var/www/app",
    "src_port": 2222,
    "dest_address": "127.0.0.1",
    "dest_user": "vagrant",
    "dest_passw": "vagrant",
    "dest_port": 2200,
    "dest_wpath": "/var/www/app/"
}
```

######Normal flow where destination user is root
![Alt text](http://i.imgur.com/AjfHpej.png)
```
python3 main.py -j file.json
```

######Normal flow where destination user is not root, but has sudo access
![Alt text](http://i.imgur.com/SRpNAUB.png)
```
python3 main.py -j file.json --dest-sudo
```

######Normal without posts
![Alt text](http://i.imgur.com/gXMXpyv.png)
```
python3 main.py -j file.json --no-posts
```

######Normal without users
![Alt text](http://i.imgur.com/MJTm1pi.png)
```
python3 main.py -j file.json --no-users
```

######Fast copy flow
For the fast copy flow you need to add the following key in the json file (because the fast copy needs access without password):
```
"dest_filekey": "<path_of_your_vagrantfile>/.vagrant/machines/default/virtualbox/private_key"
```

![Alt text](http://i.imgur.com/0wOoB3U.png)
```
python3 main.py -j file.json --fast-copy
```


####Destination machine
######Fix destination url
The json file contains:
```
{
    "dest_address": "192.168.123.91",
    "dest_user": "vagrant",
    "dest_passw": "vagrant",
    "dest_wpath": "/var/www/app/"
}
```

![Alt text](http://i.imgur.com/2BclvSJ.png)

```
# destination.local is the current url registered for wordpress (it is a link to 192.168.123.91 in my /etc/hosts)
python3 main.py -j fix.json --fix-destination-hostname --current-site destination.local --new-site 192.168.123.91
```
