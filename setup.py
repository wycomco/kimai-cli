from setuptools import setup

setup(
    name='Kimai CLI',
    version='0.1',
    py_modules=['kimai'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        kimai=kimai:cli
    '''
)
