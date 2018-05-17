from setuptools import setup

setup(
    name='kimai-cli',
    version='0.3.1',
    author='Kai Sassnowski',
    author_email='me@kai-sassnowski.com',
    scripts=['bin/kimai-complete.sh'],
    py_modules=['cli', 'kimai', 'config', 'dates', 'favorites'],
    python_requires='>3.5.2',
    install_requires=[
        'click',
        'requests',
        'tabulate',
        'PyYAML',
        'parsedatetime',
    ],
    entry_points='''
        [console_scripts]
        kimai=cli:cli
    '''
)
