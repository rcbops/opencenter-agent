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

import fixtures
import os
import socket
import testtools
import unittest

from roushagent.modules import output_manager
from roushagent import utils


class FakeSocket(object):
    def __init__(self, protocol, transport):
        self.sent = []

    def connect(self, ip_port):
        pass

    def shutdown(self, kind):
        pass

    def close(self):
        pass

    def send(self, data):
        self.sent.append(data)
        return len(data)


class FakeSocketSendFails(FakeSocket):
    def send(self, data):
        raise Exception('send failed')


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

    def test_handle_logfile_no_payload(self):
        with utils.temporary_directory() as path:
            om = output_manager.OutputManager(path)
            out = om.handle_logfile({'action': 'modules.load',
                                     'payload': {}})
            self.assertEqual(out['result_code'], 1)

    def test_handle_logfile_no_such_logfile(self):
        with utils.temporary_directory() as path:
            with utils.temporary_directory() as logdir:
                om = output_manager.OutputManager(path)
                om.config = {'main': {'trans_log_dir': logdir}}
                out = om.handle_logfile({'action': 'modules.load',
                                         'payload': {'task_id': '42',
                                                     'dest_ip': '127.0.0.1',
                                                     'dest_port': 4242}})
                self.assertEqual(out['result_code'], 1)
                self.assertEqual(out['result_str'],
                                 'no such transaction log file')

    def test_handle_logfile_remote_connection_failed(self):
        with utils.temporary_directory() as path:
            with utils.temporary_directory() as logdir:
                om = output_manager.OutputManager(path)
                om.config = {'main': {'trans_log_dir': logdir}}

                with open(os.path.join(logdir, 'trans_42.log'), 'w') as f:
                    f.write('This\nis\na\nlog\nfile')

                out = om.handle_logfile({'action': 'logfile.tail',
                                         'payload': {'task_id': '42',
                                                     'dest_ip': '127.0.0.1',
                                                     'dest_port': 4242}})
                self.assertEqual(out['result_code'], 1)
                self.assertEqual(out['result_str'],
                                 '[Errno 111] Connection refused')

    def test_handle_logfile_tail(self):
        sock = FakeSocket(socket.AF_INET, socket.SOCK_STREAM)
        with utils.temporary_directory() as path:
            with utils.temporary_directory() as logdir:
                om = output_manager.OutputManager(path)
                om.config = {'main': {'trans_log_dir': logdir}}

                with open(os.path.join(logdir, 'trans_42.log'), 'w') as f:
                    f.write('This\nis\na\nlog\nfile')

                out = om.handle_logfile({'action': 'logfile.tail',
                                         'payload': {'task_id': '42',
                                                     'dest_ip': '127.0.0.1',
                                                     'dest_port': 4242}},
                                        sock=sock)
                self.assertEqual(out['result_code'], 0)
                self.assertNotEqual(sock.sent, [])

    def test_handle_logfile_tail_socket_fail(self):
        self.useFixture(fixtures.MonkeyPatch('socket.socket',
                                             FakeSocketSendFails))

        with utils.temporary_directory() as path:
            with utils.temporary_directory() as logdir:
                om = output_manager.OutputManager(path)
                om.config = {'main': {'trans_log_dir': logdir}}

                with open(os.path.join(logdir, 'trans_42.log'), 'w') as f:
                    f.write('This\nis\na\nlog\nfile')

                out = om.handle_logfile({'action': 'logfile.tail',
                                         'payload': {'task_id': '42',
                                                     'dest_ip': '127.0.0.1',
                                                     'dest_port': 4242}})
                self.assertEqual(out['result_code'], 1)
                self.assertEqual(out['result_str'],
                                 'remote socket disconnect')

    def fake_sleep(self, duration):
        self.sleep_count += 1
        if self.sleep_count < 11:
            self.sleep_writes_to.write('This is more data!\n')
            self.sleep_writes_to.flush()

    def test_handle_logfile_watch(self):
        sock = FakeSocket(socket.AF_INET, socket.SOCK_STREAM)
        self.useFixture(fixtures.MonkeyPatch('time.sleep', self.fake_sleep))

        with utils.temporary_directory() as path:
            with utils.temporary_directory() as logdir:
                om = output_manager.OutputManager(path)
                om.config = {'main': {'trans_log_dir': logdir}}

                with open(os.path.join(logdir, 'trans_42.log'), 'w') as f:
                    f.write('This\nis\na\nlog\nfile')

                    self.sleep_count = 0
                    self.sleep_writes_to = f

                    out = om.handle_logfile(
                        {'action': 'logfile.watch',
                         'payload': {'task_id': '42',
                                     'dest_ip': '127.0.0.1',
                                     'dest_port': 4242,
                                     'timeout': 10}},
                        sock=sock)
                    self.assertEqual(out['result_code'], 0)

                    # NOTE(mikal): this one is a little complicated. The
                    # timeout is from the last bit of seen data... So, because
                    # we return data for the first ten sleeps, we expect to
                    # sleep 20 times before we timeout.
                    self.assertEqual(self.sleep_count, 20)

                    self.assertNotEqual(sock.sent, [])
                    self.assertEqual(len(sock.sent), 10)


if __name__ == '__main__':
    unittest.main()
