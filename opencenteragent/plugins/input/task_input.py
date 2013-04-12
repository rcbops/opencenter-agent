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
import sys
import socket
import threading
import time
from requests import ConnectionError

from opencenterclient.client import OpenCenterEndpoint
from opencenteragent.utils import detailed_exception

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
        self.running = False
        self._maybe_init()

    def node_deleted(self):
        """Handle this node being deleted in the opencenter server."""

        message = (
            'This node was previously registered as %s, however '
            'that node ID is no longer recognised by the server. '
            'This agent will now exit. If you wish to re-register'
            ' this node with the server, please delete %s and '
            'restart the agent' % (
                open(self.hostidfile).read(),
                self.hostidfile
            ))

        LOG.error(message)
        os._exit(1)

    def register(self):
        """Register with the OpenCenter server.

        Registration requires two calls to whoami:

        1) Call whoami with a hostname
            This allocates the node ID in opencenter, creates the node object
            and an attribute 'registered' which is false.

        2) Call whoami with the node_id returned in the first call.
            This sets the new node's parent_id and changes the registered
            attribute to true.

        """

        #Return if we are already registered.
        if self.host_id:
            return True

        host_id = None

        reg_file = '.'.join((self.hostidfile, 'registering'))

        # Node may be semi registered, try reading ID from
        # registering file.
        try:
            host_id = int(open(reg_file).read())
            LOG.info('Agent Registration: Resuming partially '
                     'completed registation. ID %s read '
                     'from registering file.' % host_id)
        except:
            # Doesn't matter if this file can't be read.
            pass

        try:
            if not host_id:
                # Get ID from hostname - This will allocate a new ID in
                # opencenter and create a node with attrs.registered=false
                resp = self.endpoint.whoami(hostname=self.name)
                host_id = resp.json['node_id']
                LOG.info('Initial connection: Opencenter ID allocated: %s' %
                         (host_id))

            # Write ID to temporary state file.
            dirs = reg_file.rpartition(os.sep)[0]
            if not os.path.exists(dirs):
                os.makedirs(dirs)
            with open(reg_file, 'wb') as f:
                f.write(str(host_id))

            # Complete registration by calling whoami with host_id. If this
            # is successful, move the temporary file to the hostidfile
            # location specified in configuration, and set self.host_id.
            resp = self.endpoint.whoami(node_id=host_id)
            if resp.json['node']['id'] == host_id:
                os.rename(reg_file, self.hostidfile)
                self.host_id = host_id
                LOG.info('Registration Complete: Verified ID: %s' %
                         self.host_id)
            else:
                #Second stage registration failed - IDs don't match
                try:
                    # Remove registration temp file, so that registration is
                    # started from scratch next time.
                    os.path.remove(reg_file)
                except:
                    pass
                LOG.error('Registration Failed: Node ID mismatch.')
                return False

        except KeyError:
            LOG.error('Unable to get node ID: %s %s' % (resp['message'],
                                                        detailed_exception()))
            return False

        except (IOError, OSError):
            LOG.error('Error storing node ID: %s' % detailed_exception())
            return False

        return True

    def verify_id(self):
        try:
            LOG.debug('verify_id, local_id: %s' % self.host_id)
            resp = self.endpoint.whoami(node_id=self.host_id)
            LOG.debug('verify_id, response status code: %s' % resp.status_code)
            return resp.json['node']['id'] == self.host_id
        except Exception:
            LOG.error("verify_id exception: " + detailed_exception())
            return False
        finally:
            try:
                if resp.status_code == 404:
                    self.node_deleted()
            except (UnboundLocalError, AttributeError):
                LOG.error(detailed_exception())
                pass

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
            # Never successfully registered - otherwise host_id would have
            # been read from hostidfile.
            self.register()

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

            if not (self._maybe_init() and self.verify_id()):
                time.sleep(15)
                continue

            try:
                task = self.endpoint.nodes[self.host_id].task_blocking
            except ConnectionError:
                time.sleep(15)
            except KeyError as e:
                LOG.error(e)
                self.node_deleted()
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

        while (blocking
               and len(self.pending_tasks) == 0
               and self.running
               ):
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
            host_id = int(f.read())
    except IOError as e:
        if e.errno == errno.ENOENT:
            host_id = None
        else:
            raise e
    except ValueError as e:
        LOG.error('Couldn\'t read integer from host id file: %s' % hostidfile)
        host_id = None

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
