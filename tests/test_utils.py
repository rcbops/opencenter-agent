#!/usr/bin/env python

import unittest
import logging

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

if __name__ == '__main__':
    unittest.main()
