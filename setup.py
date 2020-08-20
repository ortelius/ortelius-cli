from distutils.core import setup
import setuptools

setup(
    setup_requires=['wheel'],
    url='https://www.deployhub.com',
    author='Steve Taylor',
    author_email='steve@deployhub.com',
    name='deployhub',
    version='9.3.78',
    packages=['deployhub',],
    scripts=['bin/dh'],
    license='GNU AFFERO GENERAL PUBLIC LICENSE',
    long_description=open('README').read(),
    python_requires='>=3.6',
     install_requires=[
        'click',
        'qtoml',
        'PyYAML',
        'requests',
        'configobj',
        'flatten_dict'
        ],
)
