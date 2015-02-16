#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
kindlestrip
~~~~~~~~~~~

Library to strip the penultimate record from a Mobipocket file.

"""

from setuptools import setup, find_packages

setup(
    name='kindlestrip',
    version='1.36.0',
    url='https://github.com/jefftriplett/kindlestrip',
    license='Unlicense',
    description='Strips the penultimate record from Mobipocket ebooks',
    long_description=__doc__,
    author='Paul Durrant',
    author_email='',
    maintainer='Jeff Triplett',
    maintainer_email='jeff.triplett@gmail.com',
    packages=find_packages(),
    py_modules=['kindlestrip'],
    package_data={},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities'
    ],
    entry_points={
        'console_scripts': [
            'kindlestrip = kindlestrip:main',
        ]
    },
)
