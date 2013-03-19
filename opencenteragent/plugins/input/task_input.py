#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################
#

import errno
import json
import os
import socket
import threading
import time
from requests import ConnectionError

from opencenterclient.client import OpenCenterEndpoint

name = 'taskerator'
task_getter = None


class TaskThread(threading.Thread):
    def __init__(self, endpoint, name, host_id, hostidfile):
        # python, I hate you.
        super(TaskThread, self).__init__()

        self.endpoint = None
        self.endpoint_uri = endpoint
        self.name = name
        self.producer_lock = threading.Lock()
        self.producer_condition = threading.Condition(self.producer_lock)
        self.pending_tasks = []
        self.running_tasks = {}
        self.host_id = host_id
        self.hostidfile = hostidfile
        self._maybe_init()

    def _maybe_init(self):
        if self.endpoint:
            return True
        else:
            LOG.info('Connecting to endpoint')
            try:
                self.endpoint = OpenCenterEndpoint(self.endpoint_uri)
            except ConnectionError:
                return False
            except KeyboardInterrupt:
                raise

        if not self.host_id:
            # try to find our host ID from the endpoint
            LOG.info('Initial connection: fetching host ID')
            #TODO: Fix up client to support whoami in a more
            #reasonable manner and fix this code up
            root = self.endpoint.nodes.filter(
                'facts.parent_id = None and name = "workspace"').first()
            resp = root.whoami(hostname=self.name).json
            try:
                host_id = resp['node_id']
            except KeyError:
                LOG.error('Unable to get node ID: %s' % resp['message'])
                return False
            reg_file = '.'.join((self.hostidfile, 'registering'))
            dirs = reg_file.rpartition(os.sep)[0]
            try:
                os.makedirs(dirs)
            except OSError:
                pass

            with open(reg_file, 'wb') as f:
                f.write(str(host_id))
            resp = root.whoami(node_id=host_id).json
            try:
                node = resp['node']
            except KeyError:
                LOG.error('Unable to get node ID: %s' % resp['message'])
                return False
            if node['id'] == host_id:
                os.rename(reg_file, self.hostidfile)
                self.host_id = node['id']
            else:
                LOG.error('Node ID mismatch.')
                return False

        # update the module list
        self.producer_lock.acquire()
        task = {'action': 'modules.list',
                'payload': {},
                'id': -1}
        self.pending_tasks.append(task)
        self.producer_condition.notify()
        LOG.debug('added module_list task to work queue')
        self.producer_lock.release()
        self.producer_lock.acquire()
        task = {'action': 'modules.actions',
                'payload': {},
                'id': -1}
        self.pending_tasks.append(task)
        self.producer_condition.notify()
        LOG.debug('added module_list task to work queue')
        self.producer_lock.release()

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

                    # update the node to show we are running this task
                    myself = self.endpoint.nodes[self.host_id]
                    myself._request_get()
                    myself.task_id = task['id']
                    myself.save()

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
                if txid > 0:
                    # update the db
                    task = self.endpoint.tasks[txid]
                    task._request_get()
                    task.state = 'done'
                    task.result = result
                    task.save()
                    del self.running_tasks[txid]

                    myself = self.endpoint.nodes[self.host_id]
                    myself._request_get()
                    if myself.task_id == task['id']:
                        myself.task_id = None
                        myself.save()

                elif txid == -1:
                    # module list?
                    if result['result_code'] == 0:
                        newattr = self.endpoint.attrs.new(
                            node_id=self.host_id,
                            key=result['result_data']['name'],
                            value=result['result_data']['value'])
                        newattr.save()

            except ConnectionError:
                # FIXME(rp):
                # we should enqueue the task into a "retry update" list
                # so we can update it once we get back to a connected
                # state
                pass

        self.producer_lock.release()


class TaskGetter:
    def __init__(self, endpoint, name, host_id, hostidfile):
        self.endpoint = endpoint
        self.name = name
        self.host_id = host_id
        self.hostidfile = hostidfile
        self.running = False
        self.server_thread = None

    def run(self):
        if self.running:
            raise RuntimeError

        self.server_thread = TaskThread(self.endpoint, self.name,
                                        self.host_id, self.hostidfile)
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


def setup(config=None):
    global task_getter
    if config is None:
        config = {}

    hostidfile = global_config['main']['hostidfile']
    name = config.get('hostname', socket.getfqdn().strip())
    try:
        with open(hostidfile) as f:
            host_id = f.read()
    except IOError as e:
        if e.errno == errno.ENOENT:
            host_id = None
        else:
            raise e
    endpoint = global_config.get('endpoints', {}).get(
        'admin', 'http://localhost:8080/admin')

    task_getter = TaskGetter(endpoint, name, host_id, hostidfile)
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
