"""Setup config for the module."""

import setuptools

from distutils.core import setup

setup(
    setup_requires=['wheel'],
    url='https://ortelius.io',
    project_urls={ 
        'Project Repo': 'https://github.com/ortelius/compupdate',
        'Issues': 'https://github.com/ortelius/ortelius/issues',
        'CLI Documentation': 'https://github.com/ortelius/compupdate/blob/main/doc/dh.md',
        'Python API Documentation': 'https://github.com/ortelius/compupdate/blob/main/doc/deployhub.md',
        'Jenkinsfile Example': 'https://github.com/ortelius/compupdate/blob/main/Jenkinsfile'
        }, 
    author='Steve Taylor',
    author_email='steve@deployhub.com',
    name='deployhub',
    version='9.3.155',
    packages=['deployhub',],
    scripts=['bin/dh', 'bin/helminfo.sh'],
    license='GNU AFFERO GENERAL PUBLIC LICENSE',
    long_description=open('doc/dh.md').read(),
    long_description_content_type="text/markdown",
    python_requires='>=3.6',
     install_requires=[
        'click',
        'qtoml',
        'PyYAML',
        'requests',
        'configobj',
        'flatten_dict'
        ],
    include_package_data=True
)
