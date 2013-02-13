#!/usr/bin/env python
# 
# Copyright 2013, Rackspace US, Inc. 
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

import fixtures
import os
import testtools
import unittest

from roushagent.modules import manager
from roushagent import utils


class TestModuleManager(testtools.TestCase):
    def fake_load_file(self, path):
        self.files_loaded += 1

    def test_load_directory_empty(self):
        with utils.temporary_directory() as path:
            self.files_loaded = 0

            m = manager.Manager(path)
            m._load_file = self.fake_load_file
            m._load_directory(path)

            self.assertEqual(self.files_loaded, 0)

    def test_load_directory_empty(self):
        with utils.temporary_directory() as path:
            os.mkdir(os.path.join(path, 'dir'))
            with open(os.path.join(path, 'file'), 'w') as f:
                f.write('fdsjkghfgjk')
            with open(os.path.join(path, 'file.py'), 'w') as f:
                f.write('fdsjkghfgjk')

            self.files_loaded = 0

            m = manager.Manager(path)
            m._load_file = self.fake_load_file
            m._load_directory(path)

            self.assertEqual(self.files_loaded, 1)

    def test_load_file(self):
        with utils.temporary_directory() as path:
            subdir_path = os.path.join(path, 'dir')
            os.mkdir(subdir_path)
            single_file = os.path.join(path, 'file.py')
            with open(single_file, 'w') as f:
                f.write('fdsjkghfgjk')
            with open(os.path.join(subdir_path, 'file.py'), 'w') as f:
                f.write('fdsjkghfgjk')
            with open(os.path.join(subdir_path, 'file2.py'), 'w') as f:
                f.write('fdsjkghfgjk')

            self.files_loaded = 0
            m = manager.Manager(single_file)
            m._load_file = self.fake_load_file
            m.load(single_file)
            self.assertEqual(self.files_loaded, 1)

            self.files_loaded = 0
            m = manager.Manager(subdir_path)
            m._load_file = self.fake_load_file
            m.load(subdir_path)
            self.assertEqual(self.files_loaded, 2)


if __name__ == '__main__':
    unittest.main()
