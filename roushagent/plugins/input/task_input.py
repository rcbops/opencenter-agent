#!/usr/bin/env python

import json
import os
import threading
import time
from requests import ConnectionError

from roushclient.client import RoushEndpoint

name = 'taskerator'
task_getter = None


class TaskThread(threading.Thread):
    def __init__(self, endpoint, hostname, cert=None, roush_ca=None):
        # python, I hate you.
        super(TaskThread, self).__init__()

        self.endpoint = None
        self.endpoint_uri = endpoint
        self.hostname = hostname
        self.producer_lock = threading.Lock()
        self.producer_condition = threading.Condition(self.producer_lock)
        self.pending_tasks = []
        self.running_tasks = {}
        self.host_id = None
        self.cert = cert
        self.roush_ca = roush_ca
        self._maybe_init()

    def _maybe_init(self):
        if self.endpoint:
            return True
        else:
            LOG.info('Connecting to endpoint')

            try:
                self.endpoint = RoushEndpoint(self.endpoint_uri,
                                              self.cert,
                                              self.roush_ca)
            except ConnectionError:
                return False
            except KeyboardInterrupt:
                raise

        if not self.host_id:
            # try to find our host ID from the endpoint
            LOG.info('Initial connection: fetching host ID')

            for node in self.endpoint.nodes.filter("hostname='%s'" % (
                    self.hostname)):
                self.host_id = node.id

            if not self.host_id:
                # make a new node entry for this host
                LOG.info('Creating new host entry')
                node = self.endpoint.nodes.new(hostname=self.hostname,
                                               backend='unprovisioned',
                                               backend_state='unknown')
                node.save()
                self.host_id = node.id

                LOG.info('New host ID: %d' % self.host_id)

        return True

    def stop(self):
        self.endpoint = None
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            task = None

            if not self._maybe_init():
                time.sleep(15)
                continue

            try:
                task = self.endpoint.nodes[self.host_id].task_blocking
            except ConnectionError:
                time.sleep(15)
            except KeyboardInterrupt:
                raise

            if task:
                self.producer_lock.acquire()
                if task.id not in [x['id'] for x in self.pending_tasks]:
                    LOG.debug('Found new pending task with id %s' % task.id)

                    # this should be done on the server side while
                    # locked to avoid races
                    task.state = 'running'
                    task.save()

                    self.pending_tasks.append(task.to_hash())
                    self.producer_condition.notify()
                    LOG.debug('added task to work queue' % task.to_hash())
                self.producer_lock.release()

        self.running = False

    def fetch(self, blocking=True):
        # we'll assume any task we've marked as running
        # is under way, and we'll only return new pending tasks.
        retval = {}

        LOG.debug("fetching new work item")
        self.producer_lock.acquire()

        while(blocking and len(self.pending_tasks) == 0):
            self.producer_condition.wait()

        if len(self.pending_tasks) > 0:
            LOG.debug('Found %d queued tasks' % len(self.pending_tasks))

            task = self.pending_tasks.pop()
            LOG.debug('Preparing to process task: %s' % task)
            retval = {'id': task['id'],
                      'action': task['action'],
                      'payload': task['payload']}

            LOG.debug('Marking task %s as running' % task['id'])

            # throw it into the running list -- I don't know that we really
            # need this list, but meh.
            self.running_tasks[retval['id']] = retval

        self.producer_lock.release()
        return retval

    def result(self, txid, result):
        self.producer_lock.acquire()
        if txid in self.running_tasks.keys():
            try:
                # update the db
                task = self.endpoint.tasks[txid]
                task.state = 'done'
                task.result = result
                task.save()
                del self.running_tasks[txid]
            except ConnectionError:
                # FIXME(rp):
                # we should enqueue the task into a "retry update" list
                # so we can update it once we get back to a connected
                # state
                pass

        self.producer_lock.release()


class TaskGetter:
    def __init__(self, endpoint, hostname, cert=None, roush_ca=None):
        self.endpoint = endpoint
        self.hostname = hostname
        self.running = False
        self.server_thread = None
        self.cert = cert
        self.roush_ca = roush_ca

    def run(self):
        if self.running:
            raise RuntimeError

        self.server_thread = TaskThread(self.endpoint,
                                        self.hostname,
                                        self.cert,
                                        self.roush_ca)
        self.server_thread.setDaemon(True)
        self.server_thread.start()
        self.running = True

    def stop(self):
        self.running = False
        self.server_thread.stop()
        self.server_thread.join(5)
        self.server_thread.terminate()

    def fetch(self):
        return self.server_thread.fetch()

    def result(self, txid, result):
        return self.server_thread.result(txid, result)


def setup(config={}):
    global task_getter

    hostname = config.get('hostname', os.popen('hostname -f').read().strip())
    endpoint = config.get('endpoint', 'http://localhost:8080')
    cert = (config.get('cert', None), config.get('cert_key', None))
    roush_ca = config.get('roush_ca', None)
    task_getter = TaskGetter(endpoint, hostname, cert, roush_ca)
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
