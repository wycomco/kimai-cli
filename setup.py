import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

packages = ['kimai']

requires = [
    'click',
    'requests',
    'tabulate',
    'PyYAML',
    'parsedatetime',
    'fuzzyfinder',
    'prompt_toolkit',
]

about = {}
with open(os.path.join(here, 'kimai', '__version__.py'), 'r') as f:
    exec(f.read(), about)

setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    license=about['__license__'],
    scripts=['bin/kimai-complete.sh'],
    packages=packages,
    package_dir={'kimai': 'kimai'},
    include_package_data=True,
    python_requires='>3.5.2',
    install_requires=requires,
    entry_points='''
        [console_scripts]
        kimai=kimai.cli:cli
    '''
)
