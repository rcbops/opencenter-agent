#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def find_files(path_tuples):
    output_array = []

    for (path, destination) in path_tuples:

        if os.path.isdir(path):
            for d in os.walk(path):
                if len(d[2]) != 0:
                    output_dir = d[0].replace(path, destination)
                    output_files = ["%s/%s" % (d[0], x) for x in d[2]]
                    output_array.append((output_dir, output_files))
        else:
            output_array.append((destination, [path]))

    return output_array

setup(
    name='roushagent',
    version='0.1',
    author='Rackspace US, Inc.',
    description=('Yet another pluggable, modular host agent'),
    license='Apache2',
    url='https://github.com/rpedde/roush-agent',
    long_description=read('README'),
    packages=find_packages(),
    data_files=find_files([['roushagent/plugins', 'share/roush-agent/plugins'],
                           ['roush-agent.py', 'bin']])
)
