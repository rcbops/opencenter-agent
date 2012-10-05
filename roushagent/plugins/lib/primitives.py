#!/usr/bin/env python

import json
import time
import threading
import logging

from roushclient.client import RoushEndpoint
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
            action = vals['primitive']
            parameters = vals['parameters']

            del vals['primitive']
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

    def primitive_set_backend(self, state_data, backend=None, backend_state=None):
        for node in state_data['nodes']:
            if backend:
                self.endpoint.nodes[node].backend = backend
            if backend_state:
                self.endpoint.nodes[node].backend_state = backend_state

            self.endpoint.nodes[node].save()
        return self._success(state_data)

    def primitive_log(self, state_data, msg='default msg'):
        self.logger.debug(msg)
        self.logger.debug('state_data: %s' % state_data)
        return self._success(state_data)

    def primitive_run_task(self, state_data, action, payload={}, timeout=3600, poll_interval=5):
        if not 'nodes' in state_data:
            return self._failure(state_data, result_str='no node list for primitive "run_task"')

        result_list = {}

        for node in state_data['nodes']:
            task_id = self._submit_task(node, action, payload)
            if task_id:
                self.logger.debug('Submitted task %d on node %d' % (task_id, node))
                result_list[node] = task_id
            else:
                self.logger.debug('Could not submit task on node %d' % (node,))

                # take this node out of the run list
                self._fail_node(state_data, node)

        # wait for all the submitted tasks
        self.logger.debug('Waiting for submitted tasks')

        success_tasks, fail_tasks = self._wait_for_tasks(result_list, timeout, poll_interval)

        for node in fail_tasks.keys():
            self._fail_node(state_data, node)

        # should append to the run log
        if len(state_data['nodes']) > 0:
            return self._success(state_data, result_str='task runner succeeded')

        return self._failure(state_data, result_str='no successful task executions.')

    def primitive_install_chef(self, state_data):
        # strategy: find the chef server, run the "get_validation_pem" task, and then
        # run the install_chef task on the nodes with the found validation pem
        chef_server = self.endpoint.nodes.filter("backend='chef-server'").first()
        if not chef_server:
            return self._failure(state_data, result_str='cannot find a chef server')

        task_result, _ = self.primitive_run_task({'nodes': chef_server.id}, action='get_chef_info')
        if task_result['result_code'] != 0:
            return self._failure(state_data, result_str='could not get chef info from server')

        validation_pem = task_result['result_data']['validation_pem']
        chef_endpoint = task_result['result_data']['chef_endpoint']

        # now that we have the info we need, we'll go ahead and run the job
        return self.primitive_run_task(state_data, 'install_chef',
                                       payload={'CHEF_SERVER': chef_endpoint,
                                                'CHEF_VALIDATOR':  validation_pem})

    def _success(self, state_data, result_str='success', result_data={}):
        return self._result(state_data, 0, result_str, result_data)

    def _failure(self, state_data, result_code=1, result_str='failure', result_data={}):
        return self._result(state_data, result_code, result_str, result_data)

    def _result(self, state_data, result_code, result_str, result_data):
        return ({'result_code': result_code,
                'result_str': result_str,
                'result_data': result_data}, state_data)

    def _fail_node(self, state_data, node):
        state_data['nodes'].remove(node)
        if not 'fails' in state_data:
            state_data['fails'] = []
        state_data['fails'].append(node)

    # submit a task and return the task ID
    def _submit_task(self, node, action, payload):
        node_id = node

        new_task = self.endpoint.tasks.create()
        new_task.action = action
        new_task.payload = payload
        new_task.node_id = node_id
        new_task.state = 'pending'

        new_task.save()
        self.logger.debug('submitting "%s" task as %d' % (action, new_task.id))
        return new_task.id

    # given a dict of node/tasks, wait for each task to
    # complete, and return results as two dicts: a dict of successful
    # tasks and a dict of unsuccessful tasks in the following format:
    #
    # { node_id: { 'task': task_id,
    #              'result': { result blob },
    #   ....
    # }
    def _wait_for_tasks(self, task_list, timeout, poll_interval=5):
        start_time = time.time()

        success_tasks = {}
        failed_tasks = {}

        while(len(task_list) > 0 and ((time.time() - start_time) < timeout)):
            for node, task in task_list.items():
                task_obj = self.endpoint.tasks[task]
                # force a refresh
                task_obj._request('get')
                if task_obj.state != 'pending' and task_obj.state != 'running':
                    # task is done.
                    if task_obj.state in ['timeout', 'cancelled']:
                        # uh oh, that's bad.
                        failed_tasks[node] = {'task': task,
                                              'result': {'result_code': 1,
                                                         'result_msg': 'Task aborted: %s' % task_obj.state,
                                                         'result_data': {}}}
                    else:
                        # done
                        self.logger.debug('Task %d completed' % task)
                        result = task_obj.result
                        self.logger.debug('Task output: %s' % result)

                        result_entry = {'task': task,
                                        'result': result }

                        if result['result_code'] == 0:
                            success_tasks[node] = result_entry
                        else:
                            failed_tasks[node] = result_entry

                    del task_list[node]

            time.sleep(poll_interval)

        return (success_tasks, failed_tasks)

if __name__ == '__main__':
    pass
