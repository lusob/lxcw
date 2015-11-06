from setuptools import setup

setup(
    name='lxcw',
    version='0.4',
    py_modules=['lxcw'],
    install_requires=[
        'ansible',
        'Click',
    ],
    entry_points='''
        [console_scripts]
        lxcw=lxcw:cli
    ''',
)
