#!/usr/bin/env python

import json
import time
import threading
import logging

from apiclient import RoushEndpoint
from state import StateMachine, StateMachineState

# primitive functions for orchestration.
class OrchestratorTasks:
    def __init__(self, endpoint='http://localhost:8080', logger=None):
        self.endpoint = RoushEndpoint(endpoint)
        self.logger = logger
        if not logger:
            self.logger = logging.getLogger()

    def sm_eval(self, sm_dict, input_state):
        def otask(fn, *args, **kwargs):
            def outer(input_state, **outer_args):
                kwargs.update(outer_args)
                return fn(input_state, *args, **kwargs)
            return outer

        sm = StateMachine(input_state)
        if 'start_state' in sm_dict:
            sm.set_state(sm_dict['start_state'])

        for state, vals in sm_dict['states'].items():
            action = vals['action']
            parameters = vals['parameters']

            del vals['action']
            del vals['parameters']

            if not hasattr(self, 'primitive_%s' % action):
                self.logger.debug('cannot find primitive "%s"' % action)
                return ({ 'result_code': 1,
                          'result_str': 'cannot find primitive "%s"' % action,
                          'result_data': {}},{})

            fn = otask(getattr(self,'primitive_%s' % action), **parameters)
            sm.add_state(state, StateMachineState(advance=fn, **vals))

        result_data, end_state = sm.run_to_completion()
        return (result_data, end_state)

    def primitive_log(self, state_data, msg='default msg'):
        self.logger.debug(msg)
        self.logger.debug('state_data: %s' % state_data)
        return ({'result_code': 0,
                 'result_str': 'success',
                 'result_data': {}}, state_data)

    def primitive_filter(self, state_data, criteria=None):
        if criteria:
            # do some real filtering here
            self.logger.debug('popping a node')
            state_data['nodes'].pop()
            return ({'result_code': 0,
                     'result_str': 'filtered nodes',
                     'result_data': {}}, state_data)
        else:
            return ({'result_code': 1,
                     'result_str': 'no state filter criteria specified',
                     'result_data': {}}, state_data)

    # submit a task and return the task ID
    def submit_task(self, node, action, payload):
        node_id = node

        new_task = self.endpoint.Task()
        new_task.action = action
        new_task.payload = json.dumps(payload)
        new_task.node_id = node_id
        new_task.state = 'pending'

        new_task.save()
        self.logger.debug('submitting "%s" task as %d' % (action, new_task.id))
        return new_task.id

    # given a list of tasks, wait for each task to
    # complete, and return aggregate status (success/fail)
    def wait_for_tasks(self, task_list, timeout, poll_interval = 2):
        start_time = time.time()
        success = True

        complete_tasks = []

        while(len(task_list) > 0 and ((time.time() - start_time) < timeout)):
            for task in task_list:
                task_obj = self.endpoint.tasks[task]
                # force a refresh
                task_obj._request('get')
                if task_obj.state != 'pending' and task_obj.state != 'running':
                    # task is done.
                    task_list.remove(task)
                    complete_tasks.append(task)

                    if task_obj.state in ['timeout', 'cancelled']:
                        success = False
                    else:
                        # done
                        self.logger.debug('Task %d completed' % task)
                        result = json.loads(task_obj.result)
                        self.logger.debug('Task output: %s' % result)
                        success = success and (result['result_code'] == 0)
                        self.logger.debug('Success: %s' % success)

            time.sleep(poll_interval)

        if len(task_list) > 0 or not success:
            return False

        return True


if __name__ == '__main__':
    pass
