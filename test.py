#!/usr/bin/env python

import unittest
import logging

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

if __name__ == '__main__':
    unittest.main()
