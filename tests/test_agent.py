#!/usr/bin/env python

import fixtures
import logging
import sys
import testtools
import unittest

from roushagent import RoushAgent

# Suppress WARNING logs
LOG = logging.getLogger('output')
LOG.setLevel(logging.ERROR)


class TestRoushAgentWorking(unittest.TestCase):
    def setUp(self):
        self.agent = RoushAgent(['-c', 'tests/roush-agent-test-working.conf'],
                                'test')
        self.output_handler = self.agent.output_handler
        self.input_handler = self.agent.input_handler
        self.result = self.agent.input_handler.fetch()
        self.result['output'] = self.output_handler.dispatch(
            self.result['input'])
        self.agent.input_handler.result(self.result)
        self.input_state = \
            self.agent.input_handler.input_plugins['input']['state']
        self.output_state = \
            self.agent.output_handler.output_plugins['output']['state']

    def tearDown(self):
        self.agent._cleanup()

    def test_input_setup(self):
        self.assertTrue(self.input_state.input_setup_called)

    def test_input_fetch(self):
        self.assertTrue(self.input_state.input_fetch_called)

    def test_input_result(self):
        self.assertEqual(self.result['input'], {'action': 'test',
                                                'id': 'test',
                                                'payload': {}})

    def test_input_teardown(self):
        # Stop it so teardown occurs
        self.agent.input_handler.stop()
        self.assertTrue(self.input_state.input_teardown_called)

    def test_output_setup(self):
        self.assertTrue(self.output_state.output_setup_called)

    def test_output_handler(self):
        self.assertTrue(self.output_state.output_handler_called)

    def test_output_result(self):
        self.assertEqual(self.result['output'], {'result_code': 0,
                                                 'result_data': None,
                                                 'result_str': 'success'})

    def test_output_teardown(self):
        # Stop it so teardown occurs
        self.agent.output_handler.stop()
        self.assertTrue(self.output_state.output_teardown_called)


class TestRoushAgentInputBroken(unittest.TestCase):
    def setUp(self):
        self.agent = RoushAgent(['-c',
                                 'tests/roush-agent-test-input-broken.conf'],
                                'test')
        self.output_handler = self.agent.output_handler
        self.input_handler = self.agent.input_handler
        self.result = self.agent.input_handler.fetch()

        # TODO: Make not suck plz
        try:
            self.result['output'] = self.output_handler.dispatch(
                self.result['input'])
            self.agent.input_handler.result(self.result)
        except KeyError:
            self.key_error = True

        self.input_state = \
            self.agent.input_handler.input_plugins['input']['state']
        self.output_state = \
            self.agent.output_handler.output_plugins['output']['state']

    def tearDown(self):
        self.agent._cleanup()

    def test_input_setup(self):
        self.assertTrue(self.input_state.input_setup_called)

    def test_input_fetch(self):
        self.assertTrue(self.input_state.input_fetch_called)

    def test_input_result(self):
        self.assertEqual(self.result['input'], {'foo': 'bar'})

    def test_input_teardown(self):
        # Stop it so teardown occurs
        self.agent.input_handler.stop()
        self.assertTrue(self.input_state.input_teardown_called)

    def test_output_setup(self):
        self.assertTrue(self.output_state.output_setup_called)

    def test_output_handler(self):
        # Output plugin never dispatched
        self.assertFalse(self.output_state.output_handler_called)

    def test_output_result(self):
        # Output plugin dispatch failed
        self.assertTrue(self.key_error)

    def test_output_teardown(self):
        # Stop it so teardown occurs
        self.agent.output_handler.stop()
        self.assertTrue(self.output_state.output_teardown_called)


class TestRoushAgentOutputBroken(unittest.TestCase):
    def setUp(self):
        self.agent = RoushAgent(['-c',
                                 'tests/roush-agent-test-output-broken.conf'],
                                'test')
        self.output_handler = self.agent.output_handler
        self.input_handler = self.agent.input_handler
        self.result = self.agent.input_handler.fetch()
        self.result['output'] = self.output_handler.dispatch(
            self.result['input'])
        self.agent.input_handler.result(self.result)
        self.input_state = \
            self.agent.input_handler.input_plugins['input']['state']
        self.output_state = \
            self.agent.output_handler.output_plugins['output']['state']

    def tearDown(self):
        self.agent._cleanup()

    def test_input_setup(self):
        self.assertTrue(self.input_state.input_setup_called)

    def test_input_fetch(self):
        self.assertTrue(self.input_state.input_fetch_called)

    def test_input_result(self):
        self.assertEqual(self.result['input'], {'action': 'test',
                                                'id': 'test',
                                                'payload': {}})

    def test_input_teardown(self):
        # Stop it so teardown occurs
        self.agent.input_handler.stop()
        self.assertTrue(self.input_state.input_teardown_called)

    def test_output_setup(self):
        self.assertTrue(self.output_state.output_setup_called)

    def test_output_handler(self):
        self.assertFalse(self.output_state.output_handler_called)

    def test_output_result(self):
        self.assertEqual(self.result['output'],
                         {'result_code': 253, 'result_data': '',
                          'result_str':
                          'no dispatcher found for action "test"'})

    def test_output_teardown(self):
        # Stop it so teardown occurs
        self.agent.output_handler.stop()
        self.assertTrue(self.output_state.output_teardown_called)


class RoushAgentNoInitialization(RoushAgent):
    """Turn off initialization to make unit testing easier."""
    def _initialize(self, argv, config_section):
        self.logger = logging.getLogger() 
        self.logger.addHandler(logging.StreamHandler(sys.stderr)) 


class ExitCalledException(Exception):
    pass


class TestInfrastructure(testtools.TestCase):
    def fake_exit(self, exit_code):
        self.exit_code_set = exit_code
        raise ExitCalledException()
        
    def test_exit_no_exception(self):
        self.exit_code_set = None
        self.useFixture(fixtures.MonkeyPatch('sys.exit', self.fake_exit))

        agent = RoushAgentNoInitialization([])

        def no_cleanup():
            pass
        agent._cleanup = no_cleanup

        self.assertRaises(ExitCalledException, agent._exit, None)
        self.assertEqual(self.exit_code_set, 0)
        
    def test_exit_exception(self):
        self.exit_code_set = None
        self.useFixture(fixtures.MonkeyPatch('sys.exit', self.fake_exit))

        agent = RoushAgentNoInitialization([])

        def no_cleanup():
            pass
        agent._cleanup = no_cleanup

        class FakeExceptionForTest(Exception):
            pass

        def bar():
            raise FakeExceptionForTest('testing 123')

        try:
            bar()
        except FakeExceptionForTest:
            self.assertRaises(ExitCalledException, agent._exit, True)
        self.assertEqual(self.exit_code_set, 1)


if __name__ == '__main__':
    unittest.main()
