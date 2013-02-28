#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################
#
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
    name='opencenteragent',
    version='0.1',
    author='Rackspace US, Inc.',
    description=('Yet another pluggable, modular host agent'),
    license='Apache2',
    url='https://github.com/rpedde/opencenter-agent',
    long_description=read('README'),
    packages=find_packages(),
    data_files=find_files([['opencenteragent/plugins',
                            'share/opencenter-agent/plugins'],
                           ['opencenter-agent.py', 'bin']])
)
