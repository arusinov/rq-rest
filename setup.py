import os
import re

from setuptools import setup, find_packages


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    If enviroment variable `VERSION_BUILD` is set, it value appended to version.
    """
    path = os.path.join(package, "__init__.py")
    init_py = open(path, "r", encoding="utf8").read()
    version_from_init = re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)
    if not os.environ.get('VERSION_BUILD'):
        return version_from_init
    else:
        return '{}-{}'.format(version_from_init, os.environ.get('VERSION_BUILD'))

setup(
    name='rq_rest',
    version=get_version("rq_rest"),
    author='Alexey Rusinov',
    author_email='lexus@sibmf.ru',
    description='rq_rest is an RQ library extension for creating background jobs '
                'via HTTP REST interface.',
    packages=find_packages(),
    #include_package_data=True,
    package_data={
        '': ['*.tpl']
    },
    install_requires=[
        'click>=5.0',
        'gunicorn>=20.0.0',
        'rq==1.3.0',
        'bottle==0.12.18',
    ],
    python_requires='>=3.5',
    entry_points={
        'console_scripts': [
            'rq-rest = rq_rest.cli:main',
        ],
    },
)