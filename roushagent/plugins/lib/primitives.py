#!/usr/bin/env python

import json
import time
import threading

from apiclient import RoushEndpoint
from multiprocessing import Pool

# primitive functions for orchestration.

class OrchestratorTasks:
    def __init__(self, endpoint = 'http://localhost:8080'):
        self.endpoint = RoushEndpoint(endpoint)

    # submit a task and return the task ID
    def submit_task(self, node, action, payload):
        node_id = node

        new_task = self.endpoint.Task()
        new_task.action = action
        new_task.payload = json.dumps(payload)
        new_task.node_id = node_id
        new_task.state = 'pending'

        new_task.save()
        return new_task.id

    # given a list of tasks, wait for each task to
    # complete, and return aggregate status (success/fail)
    def wait_for_tasks(self, task_list, timeout, poll_interval = 10):
        start_time = time.time()
        success = True

        complete_tasks = []

        while(len(task_list) > 0 and ((time.time() - start_time) < timeout)):
            for task in task_list:
                task_obj = self.endpoint.tasks[int(task)]
                if task_obj.state != 'pending' and task_obj.status != 'running':
                    # task is done.
                    task_list.remove(task)
                    complete_tasks.append(task)

                    if task_obj.state in ['timeout', 'cancelled']:
                        success = False
                    else:
                        # done
                        success = success and (task_obj.result == 0)

            time.sleep(poll_interval)

        if len(task_list) > 0 or not success:
            return False

        return True


if __name__ == '__main__':
    pass
