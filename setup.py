#!/usr/bin/env python

import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def files_for_path(path_tuples):
    output_array = []

    for (path, destination) in path_tuples:

        if os.path.isdir(path):
            for d in os.walk(path):
                if len(d[2]) != 0:
                    output_dir = d[0].replace(path, destination)
                    output_files = ["%s/%s" % (d[0], x) for x in d[2]]
                    output_array.append((output_dir,output_files))
        else:
            output_array.append((destination, [path]))

    print output_array
    return output_array

setup(
    name = 'roushagent',
    version = '0.1',
    author = 'Rackspace US, Inc.',
    description = ('Yet another pluggable, modular host agent'),
    license = 'Apache2',
    url = 'https://github.com/rpedde/roush-agent',
    long_description = read('README'),
    packages = find_packages(),
    data_files = files_for_path([['roushagent/plugins', 'share/roush-agent/plugins'],
                                 ['roush-agent.py', 'bin']])
)
