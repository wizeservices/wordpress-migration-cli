import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "wordpress-migration-cli",
    version = "0.1.0",
    author = "Cristian Velazquez",
    author_email = "cristian.vlz@wizeline.com",
    description = ("A commandline tool to migarte a wordpress site to another "
                   "domain"),
    license = "MIT",
    keywords = "wordpress migration tool",
    packages=['wordpress_migration_cli', 'wordpress_migration_cli.process'],
    long_description=read('README.md'),
    entry_points = {
            "console_scripts": [
                'wordpress-migration-cli = wordpress_migration_cli.main:main'
            ]
        }
)
