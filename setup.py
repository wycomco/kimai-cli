from setuptools import setup

setup(
    name='kimai-cli',
    version='0.2.0',
    author='Kai Sassnowski',
    author_email='me@kai-sassnowski.com',
    py_modules=['cli', 'kimai', 'config'],
    python_requires='>3.5.2',
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
