import os
from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='Kimai CLI',
    version='0.1',
    py_modules=['cli', 'kimai', 'config'],
    install_requires=required,
    entry_points='''
        [console_scripts]
        kimai=cli:cli
    '''
)
