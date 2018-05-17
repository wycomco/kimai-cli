from setuptools import setup

setup(
    name='Kimai CLI',
    version='0.1',
    py_modules=['cli', 'kimai', 'config'],
    install_requires=[
        'click',
        'requests',
        'tabulate',
        'PyYAML'
    ],
    entry_points='''
        [console_scripts]
        kimai=cli:cli
    '''
)
