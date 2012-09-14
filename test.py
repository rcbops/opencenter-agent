#!/usr/bin/env python

import unittest

from roushagent import RoushAgent

class TestRoushAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = RoushAgent(["-c", "roush-agent-test.conf"])

    def test_1_input_handler_setup(self):
        self.assertTrue(self.agent.input_handler.input_plugins['input']['state'].input_setup_called)

    def test_2_dispatch(self):
        # Actually run the thing
        self.agent._dispatch(True)

    def test_3_input_handler_fetch(self):
        self.assertTrue(self.agent.input_handler.input_plugins['input']['state'].input_fetch_called)

    def test_4_input_handler_teardown(self):
        # Stop it so teardown occurs
        self.agent.input_handler.stop()
        self.assertTrue(self.agent.input_handler.input_plugins['input']['state'].input_teardown_called)

    def test_5_output_handler_setup(self):
        self.assertTrue(self.agent.output_handler.output_plugins['output']['state'].output_setup_called)

    def test_6_output_handler_handler(self):
        self.assertTrue(self.agent.output_handler.output_plugins['output']['state'].output_handler_called)

    def test_7_output_handler_teardown(self):
        # Stop it so teardown occurs
        self.agent.output_handler.stop()
        self.assertTrue(self.agent.output_handler.output_plugins['output']['state'].output_teardown_called)

if __name__ == '__main__':
    unittest.main()
