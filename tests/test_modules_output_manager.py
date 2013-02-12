#!/usr/bin/env python

import fixtures
import os
import testtools
import unittest

from roushagent.modules import output_manager
from roushagent import utils


class TestModuleOutputManager(testtools.TestCase):
    def test_init(self):
        with utils.temporary_directory() as path:
            om = output_manager.OutputManager(path)
            self.assertTrue(len(om.dispatch_table) > 0)

    def test_register_action_duplicate(self):
        with utils.temporary_directory() as path:
            om = output_manager.OutputManager(path)
            om.dispatch_table['action'] = {'short_path': 'shortpath',
                                           'method': 'method'}
            self.assertRaises(NameError, om.register_action, 'shortpath',
                              'plugin', 'action', 'method')

    def test_actions(self):
        with utils.temporary_directory() as path:
            om = output_manager.OutputManager(path)
            self.assertTrue(len(om.actions()) > 0)

    def test_handle_modules_list(self):
        with utils.temporary_directory() as path:
            om = output_manager.OutputManager(path)
            out = om.handle_modules({'action': 'modules.list'})
            self.assertEqual(out['result_code'], 0)
            self.assertEqual(out['result_str'], 'success')
            self.assertTrue('name' in out['result_data'])
            self.assertEqual(out['result_data']['name'],
                             'roush_agent_output_modules')
            self.assertTrue('value' in out['result_data'])

    def test_handle_modules_actions(self):
        with utils.temporary_directory() as path:
            om = output_manager.OutputManager(path)
            out = om.handle_modules({'action': 'modules.actions'})
            self.assertEqual(out['result_code'], 0)
            self.assertEqual(out['result_str'], 'success')
            self.assertTrue('name' in out['result_data'])
            self.assertEqual(out['result_data']['name'],
                             'roush_agent_actions')
            self.assertTrue('value' in out['result_data'])

    def fake_loadfile(self, path):
        self.loadfile_calls += 1

    def test_handle_modules_load(self):
        with utils.temporary_directory() as path:
            om = output_manager.OutputManager(path)
            om.loadfile = self.fake_loadfile

            out = om.handle_modules({'action': 'modules.load'})
            self.assertEqual(out['result_code'], 1)
            self.assertEqual(out['result_str'],
                             'no payload specified')

            out = om.handle_modules({'action': 'modules.load',
                                     'payload': {'gerbil': True}})
            self.assertEqual(out['result_code'], 1)
            self.assertEqual(out['result_str'],
                             'no "path" specified in payload')

            out = om.handle_modules({'action': 'modules.load',
                                     'payload': {'path': '/tmp/no/such'}})
            self.assertEqual(out['result_code'], 1)
            self.assertEqual(out['result_str'],
                             'specified module does not exist')

            self.loadfile_calls = 0
            with utils.temporary_file() as path:
                out = om.handle_modules({'action': 'modules.load',
                                         'payload': {'path': path}})
                self.assertEqual(out['result_code'], 0)
                self.assertEqual(self.loadfile_calls, 1)

    def test_handle_modules_reload(self):
        with utils.temporary_directory() as path:
            om = output_manager.OutputManager(path)
            out = om.handle_modules({'action': 'modules.reload'})
            self.assertEqual(out['result_code'], 0)
            self.assertEqual(out['result_str'], 'success')

    def test_xter_to_eof(self):
        class FileLikeObject(object):
            def __init__(self, good_reads):
                self.good_reads = good_reads

            def read(self, size):
                self.good_reads -= 1
                if self.good_reads > 0:
                    return '!' * size
                return ''

        class SocketLikeObject(object):
            def __init__(self, good_writes):
                self.good_writes = good_writes

            def send(self, size):
                self.good_writes -= 1
                if self.good_writes > 0:
                    return len(size)
                return 0

        class ExceptionalSocketLikeObject(object):
            def send(self, data):
                raise Exception('Unexpected banana!')

        f = FileLikeObject(2)
        s = SocketLikeObject(100)
        self.assertTrue(output_manager._xfer_to_eof(f, s))

        f = FileLikeObject(100)
        s = SocketLikeObject(1)
        self.assertFalse(output_manager._xfer_to_eof(f, s))

        f = FileLikeObject(100)
        s = ExceptionalSocketLikeObject()
        self.assertFalse(output_manager._xfer_to_eof(f, s))


if __name__ == '__main__':
    unittest.main()
