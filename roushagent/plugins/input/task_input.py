#!/usr/bin/env python

import json
import os
import threading
import time

from roushclient.client import RoushEndpoint

name = 'taskerator'
task_getter = None


class TaskThread(threading.Thread):
    def __init__(self, endpoint, hostname):
        # python, I hate you.
        super(TaskThread, self).__init__()

        self.endpoint = RoushEndpoint(endpoint)
        self.producer_lock = threading.Lock()
        self.pending_tasks = []
        self.running_tasks = {}
        self.host_id = None

        # try to find our host ID from the endpoint
        LOG.info('Fetching host ID')

        for node in self.endpoint.nodes.filter("hostname='%s'" % hostname):
            self.host_id = node.id

        if not self.host_id:
            # make a new node entry for this host
            LOG.info('Creating new host entry')
            node = self.endpoint.nodes.new(hostname=hostname,
                                           backend='unprovisioned',
                                           backend_state='unknown')
            node.save()
            self.host_id = node.id

            LOG.info('New host ID: %d' % self.host_id)

    def stop(self):
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            # FIXME(rp): handle error cases
            task = self.endpoint.nodes[self.host_id].task
            if task and task.state == 'pending':
                self.producer_lock.acquire()
                if task.id not in [x['id'] for x in self.pending_tasks]:
                    LOG.debug('Found new pending task with id %s' % task.id)
                    self.pending_tasks.append(task.to_hash())
                    LOG.debug('added task to work queue' % task.to_hash())
                self.producer_lock.release()

            time.sleep(15)

        self.running = False

    def fetch(self, blocking=True):
        # we'll assume any task we've marked as running
        # is under way, and we'll only return new pending tasks.
        retval = {}

        LOG.debug("fetching new work item")
        self.producer_lock.acquire()
        if len(self.pending_tasks) > 0:
            LOG.debug('Found %d queued tasks' % len(self.pending_tasks))

            task = self.pending_tasks.pop()
            LOG.debug('Preparing to process task: %s' % task)
            retval = {'id': task['id'],
                      'action': task['action'],
                      'payload': task['payload']}

            LOG.debug('Marking task %s as running' % task['id'])
            # FIXME(rp): handle error
            task = self.endpoint.tasks[task['id']]
            task.state = 'running'
            task.save()

            # throw it into the running list
            self.running_tasks[retval['id']] = retval

        self.producer_lock.release()
        return retval

    def result(self, txid, result):
        self.producer_lock.acquire()
        if txid in self.running_tasks.keys():
            del self.running_tasks[txid]

            # update the db
            # FIXME(rp): handle errors
            task = self.endpoint.tasks[txid]
            task.state = 'done'
            task.result = result
            task.save()

        self.producer_lock.release()


class TaskGetter:
    def __init__(self, endpoint, hostname):
        self.endpoint = endpoint
        self.hostname = hostname
        self.running = False
        self.server_thread = None

    def run(self):
        if self.running:
            raise RuntimeError

        self.server_thread = TaskThread(self.endpoint, self.hostname)
        self.server_thread.start()
        self.running = True

    def stop(self):
        self.running = False
        self.server_thread.stop()
        self.server_thread.join()

    def fetch(self):
        return self.server_thread.fetch()

    def result(self, txid, result):
        return self.server_thread.result(txid, result)


def setup(config={}):
    global task_getter

    hostname = config.get('hostname', os.popen('hostname -f').read().strip())
    endpoint = config.get('endpoint', 'http://localhost:8080')

    task_getter = TaskGetter(endpoint, hostname)
    task_getter.run()


def teardown():
    global task_getter
    task_getter.stop()


def fetch():
    global task_getter
    return task_getter.fetch()


def result(input_data, output_data):
    global task_getter

    txid = input_data['id']
    result_hash = output_data
    return task_getter.result(txid, result_hash)
