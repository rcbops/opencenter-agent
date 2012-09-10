#!/usr/bin/env python

import json
import os
import threading
import time

import requests

name = 'taskerator'
task_getter = None


class TaskThread(threading.Thread):
    def __init__(self, endpoint, hostname):
        # python, I hate you.
        super(TaskThread, self).__init__()

        self.endpoint = endpoint
        self.producer_lock = threading.Lock()
        self.pending_tasks = []
        self.running_tasks = {}

        # try to find our host ID from the endpoint
        LOG.info('Fetching host ID')
        rc, data = self._get('/nodes/')
        if self._is_success(rc):
            restructured = dict((x['hostname'], x) for x in data['nodes'])
            if hostname in restructured.keys():
                self.host_id = restructured[hostname]['id']
                LOG.info('Found existing host ID %s' % self.host_id)
            else:
                # create an entry for this host.
                rc, data = self._post('/nodes/', {'hostname': hostname})

                if self._is_success(rc):
                    self.host_id = data['node']['id']
                    LOG.info('Created new host entry with ID %s' %
                             self.host_id)
                else:
                    LOG.error('Error creating new node object.')
                    raise RuntimeError
        else:
            LOG.error('Error getting nodes list')
            raise RuntimeError

    def _is_success(self, retcode):
        if retcode >= 200 and retcode <= 299:
            return True
        return False

    def _request(self, method, uri, data_dict=None, headers=None):
        r = None

        if method == 'GET':
            r = requests.get(uri)
        elif method == 'POST':
            r = requests.post(uri, data=data_dict,
                              headers={'content-type': 'application/json'})
        elif method == 'PUT':
            r = requests.put(uri, data=data_dict,
                             headers={'content-type': 'application/json'})
        else:
            raise ValueError

        try:
            text = r.text
        except AttributeError:
            pass
        finally:
            if not text:
                text = r.content

        if self._is_success(r.status_code):
            return (r.status_code, json.loads(text))

        return (r.status_code, text)

    def _get(self, partial_uri):
        return self._request('GET', self.endpoint + partial_uri)

    def _post(self, partial_uri, data_dict=None):
        return self._request('POST', self.endpoint + partial_uri,
                             json.dumps(data_dict))

    def _put(self, partial_uri, data_dict=None):
        return self._request('PUT', self.endpoint + partial_uri,
                             json.dumps(data_dict))

    def stop(self):
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            # FIXME(rp): handle error cases
            (rc, data) = self._get('/nodes/%s/tasks' % self.host_id)
            if self._is_success(rc) and data['state'] == 'pending':
                # we have a new pending task.
                self.producer_lock.acquire()
                if data['id'] not in [x['id'] for x in self.pending_tasks]:
                    self.pending_tasks.append(data)
                    LOG.debug('Found new pending task with id %s' % data['id'])
                self.producer_lock.release()

            time.sleep(15)

        self.running = False

    def fetch(self, blocking=True):
        # we'll assume any task we've marked as running
        # is under way, and we'll only return new pending tasks.
        retval = {}

        self.producer_lock.acquire()
        if len(self.pending_tasks) > 0:
            task = self.pending_tasks.pop()
            retval = {'id': task['id'],
                      'action': task['action'],
                      'payload': json.loads(task['payload'])}

            LOG.debug('Marking task %s as running' % task['id'])
            # FIXME(rp): handle error
            self._put('/tasks/%s' % task['id'], {'state': 'running'})

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
            self._put('/tasks/%s' % txid, {'state': 'done',
                                           'result': json.dumps(result)})
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
