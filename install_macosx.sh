#!/bin/bash

[ $UID != 0 ] && echo "Run it as root" && exit -1

which brew &> /dev/null
[ $? != 0 ] && \
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

brew list | grep -q python3
[ $? != 0 ] && brew install python3

easy_install-3.5 pip
pip3 install paramiko

rm -rf ./scp.py/
git clone https://github.com/jbardin/scp.py.git
pushd scp.py/
python3 setup.py install
popd
rm -rf ./scp.py/
