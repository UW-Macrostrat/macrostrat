from codecs import open
from os.path import abspath, dirname, join
from subprocess import call

from setuptools import Command, find_packages, setup

from cli import __version__


this_dir = abspath(dirname(__file__))
with open(join(this_dir, 'README.md'), encoding='utf-8') as file:
    long_description = file.read()


# class RunTests(Command):
#     """Run all tests."""
#     description = 'run tests'
#     user_options = []
#
#     def initialize_options(self):
#         pass
#
#     def finalize_options(self):
#         pass
#
#     def run(self):
#         """Run all tests!"""
#         errno = call(['py.test', '--cov=skele', '--cov-report=term-missing'])
#         raise SystemExit(errno)
#

setup(
    name = 'macrostrat-cli',
    version = __version__,
    description = 'Utilities for manipulating Macrostrat',
    long_description = long_description,
    url = 'https://github.com/UW-Macrostrat/macrostrat-cli',
    author = 'John J Czaplewski',
    author_email = 'jczaplewski@wisc.edu',
    license = 'CC0',
    classifiers = [
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: Public Domain',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
    ],
    keywords = 'cli',
    packages = find_packages(exclude=['docs', 'tests*']),
    install_requires = ['psycopg2', 'pymysql', 'pyyaml', 'tiletanic', 'shapely', 'fiona', 'pyproj', 'numpy', 'scipy', 'tqdm'],
    # extras_require = {
    #     'test': ['coverage', 'pytest', 'pytest-cov'],
    # },
    entry_points = {
        'console_scripts': [
            'macrostrat=cli.cli:main',
        ],
    },
    # cmdclass = {'test': RunTests},
)
