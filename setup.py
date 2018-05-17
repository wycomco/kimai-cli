from setuptools import setup

setup(
    name='Kimai CLI',
    version='0.1',
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
