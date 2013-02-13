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

import logging
import os
import unittest

from roushagent import utils

# Suppress WARNING logs
LOG = logging.getLogger('output')
LOG.setLevel(logging.ERROR)


class TestRoushUtils(unittest.TestCase):
    def test_detailed_exception(self):
        class FakeExceptionForTest(Exception):
            pass

        def bar():
            raise FakeExceptionForTest('testing 123')

        def foo():
            bar()

        try:
            foo()
        except FakeExceptionForTest:
            trace = utils.detailed_exception()
            trace_as_string = ''.join(trace)
            self.assertNotEqual(trace_as_string.find('bar()'), -1)
            self.assertNotEqual(trace_as_string.find('foo()'), -1)
            self.assertEqual(trace_as_string.find('banana()'), -1)
            self.assertNotEqual(trace_as_string.find('testing 123'), -1)


class TestTemporaryFiles(unittest.TestCase):
    def test_temporary_file(self):
        with utils.temporary_file() as filename:
            self.assertTrue(os.path.exists(filename))
        self.assertFalse(os.path.exists(filename))

    def test_temporary_directory(self):
        with utils.temporary_directory() as path:
            self.assertTrue(os.path.exists(path))
        self.assertFalse(os.path.exists(path))


if __name__ == '__main__':
    unittest.main()
