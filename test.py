#!/usr/bin/env python

import unittest
import logging

from roushagent import RoushAgent

# Suppress WARNING logs
LOG = logging.getLogger('output')
LOG.setLevel(logging.ERROR)

class TestRoushAgentWorking(unittest.TestCase):
    def setUp(self):
        self.agent = RoushAgent(["-c", "roush-agent-test.conf"])
        self.output_handler = self.agent.output_handler
        self.input_handler = self.agent.input_handler
        self.result = self.agent.input_handler.fetch()
        self.result['output'] = self.output_handler.dispatch(self.result['input'])
        self.agent.input_handler.result(self.result)
        self.input_state = self.agent.input_handler.input_plugins['input']['state']
        self.output_state = self.agent.output_handler.output_plugins['output']['state']

    def tearDown(self):
        self.agent._cleanup()

    def test_input_setup(self):
        self.assertTrue(self.input_state.input_setup_called)

    def test_input_fetch(self):
        self.assertTrue(self.input_state.input_fetch_called)

    def test_input_teardown(self):
        # Stop it so teardown occurs
        self.agent.input_handler.stop()
        self.assertTrue(self.input_state.input_teardown_called)

    def test_output_setup(self):
        self.assertTrue(self.output_state.output_setup_called)

    def test_output_handler(self):
        self.assertTrue(self.output_state.output_handler_called)

    def test_output_teardown(self):
        # Stop it so teardown occurs
        self.agent.output_handler.stop()
        self.assertTrue(self.output_state.output_teardown_called)

if __name__ == '__main__':
    unittest.main()
