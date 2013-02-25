#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
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

import time
import logging

from opencenterclient.client import OpenCenterEndpoint
from opencenteragent.utils import detailed_exception

from state import StateMachine, StateMachineState

import opencenter.backends
from opencenter.db import api as db_api


# primitive functions for orchestration.
class OrchestratorTasks:
    def __init__(self, endpoint='http://localhost:8080', logger=None,
                 parent_task_id=None, adventure_globals=None):
        self.endpoint = OpenCenterEndpoint(endpoint)
        self.logger = logger
        self.parent_task_id = parent_task_id

        self.api = db_api.api_from_endpoint(endpoint)

        self.adventure_globals = adventure_globals
        if not adventure_globals:
            self.adventure_globals = {}

        if not logger:
            self.logger = logging.getLogger()

        opencenter.backends.load()

    def add_rollback_step(self, node_id, input_state, state_value):
        if not 'rollback_plan' in input_state:
            input_state['rollback_plan'] = {}

        if not node_id in input_state['rollback_plan']:
            input_state['rollback_plan'][node_id] = {
                'start_state': 'state_1',
                'states': {'state_1':
                           {'primitive': 'noop',
                            'parameters': {}}}}
        # we have a rollback plan already
        plan = input_state['rollback_plan'][node_id]

        old_start = plan['start_state']
        state_value['on_success'] = old_start

        # yeah, pep-8, you are right.  this is WAY more readable.
        state = 'state_%d' % (int(max(map(lambda x: int(
                              x.split('_')[1]), plan['states'].keys()))) + 1)

        plan['start_state'] = state
        plan['states'][state] = state_value
        input_state['rollback_plan'][node_id] = plan

        self.logger.debug('new rollback plan for node %s: %s' % (node_id,
                                                                 plan))
        return input_state

    def backend_wrapper(self, state_data, prim_name, fn, api, *args, **kwargs):
        """
        this runs the passed backend primitive function on all the nodes
        in the input state node list.  Failed nodes are dropped into the
        fail bucket to be rolled back.

        Right now, this runs all the backend functions in series.
        Probably it should be doing this in parallel.
        """

        nodelist_length = len(state_data['nodes'])
        result_data = {}

        # we're serializing on this.  when we shift to multi-target
        # adventures in the ui, we probably want to do this in parallel,
        # _particularly_ in the case of run_task
        #
        for node in state_data['nodes']:
            try:
                task_result = fn(state_data, api, node, *args, **kwargs)
            except Exception as e:
                task_result = {'result_code': 1,
                               'result_str': '%s: %s' % (prim_name, str(e)),
                               'result_data': detailed_exception()}

            result_data[node] = task_result
            if task_result['result_code'] != 0:
                self._fail_node(state_data, node)

        log_entry = 'ran primitive %s: %d/%d completed successfully' % (
            prim_name, len(state_data['nodes']), nodelist_length)

        if len(state_data['nodes']) > 0:
            return self._success(state_data,
                                 result_str=log_entry,
                                 result_data=result_data)
        else:
            return self._failure(state_data,
                                 result_str=log_entry,
                                 result_data=result_data)

    def sm_eval(self, plan, input_state):
        def be_task(prim_name, fn, api, **kwargs):
            def wrapped(input_state, **outer_args):
                kwargs.update(outer_args)
                return self.backend_wrapper(input_state, prim_name,
                                            fn, api, **kwargs)
            return wrapped

        self.logger.info('building state machine for %s' % plan)
        sm = StateMachine(input_state)
        sm.set_state('state_0')

        for state_index, state in enumerate(plan):
            parameters = state['ns']
            primitive = state['primitive']
            timeout = state.get('timeout', 30)

            self.logger.debug('padding globals %s' % self.adventure_globals)

            parameters['globals'] = self.adventure_globals
            parameters['globals']['parent_task_id'] = self.parent_task_id

            self.logger.debug('Wrapping %s primitive' % primitive)

            if '.' in primitive:
                # this primitive comes from backends
                backend_fn = opencenter.backends.primitive_by_name(primitive)
                if not backend_fn:
                    msg = 'cannot find backend primitive "%s"' % primitive
                    self.logger.debug(msg)
                    input_state['fails'] = input_state['nodes']
                    input_state['nodes'] = []

                    return({'result_code': 1,
                            'result_str': msg,
                            'result_data': {}}, input_state)

                fn = be_task(primitive, backend_fn, self.api, **parameters)
            else:
                # this primitive comes from node tasks.
                parameters['timeout'] = timeout
                run_task = 'agent.run_task'
                backend_fn = opencenter.backends.primitive_by_name(run_task)
                fn = be_task('agent.run_task', backend_fn, self.api,
                             **{'action': primitive,
                                'payload': parameters})

            # we have the backend fn, now wrap it up.

            # solver plans are linear, so we'll jump to next step always
            # plus, we'll assume that failure goes to default failure case
            next_state = state_index + 1
            success_state = 'state_%d' % next_state

            if(next_state) == len(plan):
                success_state = 'success'

            sm.add_state(
                'state_%d' % state_index, StateMachineState(
                    advance=fn,
                    on_success=success_state))

        result_data, end_state = sm.run_to_completion()
        return (result_data, end_state)

    def primitive_noop(self, state_data):
        return self._success(state_data)

    def primitive_set_backend(self, state_data,
                              backend=None, backend_state=None):
        for node in state_data['nodes']:
            self.logger.debug('Changing node %s backend to %s/%s' % (
                node, backend, backend_state))
            node_obj = self.endpoint.nodes[node]

            old_backend = node_obj.backend
            old_backend_state = node_obj.backend_state

            if backend:
                self.logger.debug('changing backend')
                node_obj.backend = backend
            if backend_state:
                self.logger.debug('changing backend state')
                node_obj.backend_state = backend_state

            node_obj.save()

            state_data = self.add_rollback_step(node, state_data, {
                'primitive': 'set_backend',
                'parameters': {'backend': old_backend,
                               'backend_state': old_backend_state}})
        return self._success(state_data)

    def primitive_log(self, state_data, msg='default msg'):
        self.logger.debug(msg)
        self.logger.debug('state_data: %s' % state_data)
        return self._success(state_data)

    # FIXME(rp): how does save() fail?  exception?
    def primitive_set_cluster(self, state_data, cluster_id):
        for node in state_data['nodes']:
            node_obj = self.endpoint.nodes[node]
            old_cluster_id = node_obj.cluster_id
            node_obj.cluster_id = cluster_id
            node_obj.save()

            state_data = self.add_rollback_step(node, state_data, {
                'primitive': 'set_cluster',
                'parameters': {'cluster_id': old_cluster_id}})

        return self._success(state_data)

    def primitive_set_role(self, state_data, role):
        for node in state_data['nodes']:
            node_obj = self.endpoint.nodes[node]
            old_role = node_obj.role
            node_obj.role = role
            node_obj.save()

            state_data = self.add_rollback_step(node, state_data, {
                'primitive': 'set_role',
                'parameters': {'role': old_role}})

        return self._success(state_data)

    def primitive_set_fact(self, state_data, fact, value):
        for node in state_data['nodes']:
            node_obj = self.endpoint.nodes[node]

            old_value = None
            if fact in node_obj.config:
                old_value = node_obj.config[fact]

            node_obj.config[fact] = value
            node_obj.save()

            state_data = self.add_rollback_step(node, state_data, {
                'primitive': 'set_fact',
                'parameters': {'fact': fact,
                               'value': old_value}})

        return self._success(state_data)

    def primitive_run_task(self, state_data, action, payload={},
                           timeout=3600, poll_interval=5):
        if not 'nodes' in state_data:
            return self._failure(
                state_data,
                result_str='no node list for primitive "run_task"')

        result_list = {}
        output_list = {}

        for node in state_data['nodes']:
            task_id = self._submit_task(state_data, node, action, payload)
            if task_id:
                self.logger.debug('Submitted task %d on node %d' % (task_id,
                                                                    node))
                result_list[node] = task_id
            else:
                self.logger.debug('Could not submit task on node %d' % (node,))

                output_list[node] = self._failure(
                    0, result_str='could not submit task')

                # take this node out of the run list
                self._fail_node(state_data, node)

        # wait for all the submitted tasks
        self.logger.debug('Waiting for submitted tasks')

        success_tasks, fail_tasks = self._wait_for_tasks(result_list,
                                                         timeout,
                                                         poll_interval)

        for node in fail_tasks.keys():
            output_list[node] = fail_tasks[node]['result']
            self._fail_node(state_data, node)

        for node in success_tasks.keys():
            output_list[node] = success_tasks[node]['result']

        # should append to the run log
        if len(state_data['nodes']) > 0:
            return self._success(state_data,
                                 result_str='task runner succeeded',
                                 result_data=output_list)

        return self._failure(state_data,
                             result_str='no successful task executions.',
                             result_data=output_list)

    def primitive_install_chef(self, state_data):
        # strategy: find the chef server, run "get_validation_pem" task, then
        # run the install_chef task on the nodes with the found validation pem
        chef_server = self.endpoint.nodes.filter(
            "backend='chef-server'").first()
        if not chef_server:
            return self._failure(state_data,
                                 result_str='cannot find a chef server')

        task_result, _ = self.primitive_run_task({'nodes': [chef_server.id]},
                                                 action='get_chef_info')
        if task_result['result_code'] != 0:
            return self._failure(
                state_data,
                result_str='could not get chef info from server')

        validation_pem = task_result['result_data'][chef_server.id][
            'result_data']['validation_pem']
        chef_endpoint = task_result['result_data'][chef_server.id][
            'result_data']['chef_endpoint']

        # now that we have the info we need, we'll go ahead and run the job
        return self.primitive_run_task(state_data, 'install_chef',
                                       payload={
                                           'CHEF_SERVER': chef_endpoint,
                                           'CHEF_VALIDATOR':  validation_pem})

    def _success(self, state_data, result_str='success', result_data={}):
        return self._result(state_data, 0, result_str, result_data)

    def _failure(self, state_data, result_code=1,
                 result_str='failure', result_data={}):
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
    def _submit_task(self, state_data, node, action, payload):
        node_id = node

        new_task = self.endpoint.tasks.create()
        new_task.action = action
        new_task.payload = payload
        new_task.node_id = node_id
        new_task.parent_id = self.parent_task_id

        state_data = self.add_rollback_step(node_id, state_data, {
            'primitive': 'run_task',
            'parameters': {'action': 'rollback_%s' % action,
                           'payload': payload}})

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
                if task_obj.state not in ['pending', 'delivered', 'running']:
                    # task is done.
                    if task_obj.state in ['timeout', 'cancelled']:
                        # uh oh, that's bad.
                        failed_tasks[node] = {
                            'task': task,
                            'result': {
                                'result_code': 1,
                                'result_msg': 'Task aborted: %s' % (
                                    task_obj.state),
                                'result_data': {}}}
                    else:
                        # done
                        self.logger.debug('Task %d completed' % task)
                        result = task_obj.result
                        self.logger.debug('Task output: %s' % result)

                        result_entry = {'task': task,
                                        'result': result}

                        if result['result_code'] == 0:
                            success_tasks[node] = result_entry
                        else:
                            failed_tasks[node] = result_entry

                    del task_list[node]

            time.sleep(poll_interval)

        return (success_tasks, failed_tasks)

if __name__ == '__main__':
    pass
