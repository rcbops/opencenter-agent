#!/usr/bin/env python

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
