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

import netifaces
import json
import urllib2

from bashscriptrunner import BashScriptRunner
import os

name = 'chef'


def setup(config={}):
    LOG.debug('Doing setup in plugin_chef.py using bash_path %s' %
              global_config['main']['bash_path'])
    if not 'bash_path' in global_config['main']:
        LOG.error('bash_path is not set')
        raise ValueError('bash_path not set')

    if 'cookbook_channels_manifest_url' not in global_config['chef']:
        LOG.error('cookbook_channels_manifest_url is not set')
        raise ValueError('cookbook_channels_manifest_url not set')

    script_path = [os.path.join(global_config['main']['bash_path'], name)]
    env = {'OPENCENTER_BASH_DIR': global_config['main']['bash_path']}
    script = BashScriptRunner(script_path=script_path, log=LOG,
                              environment=env)
    config['cookbook_channels_manifest_url'] \
        = global_config['chef']['cookbook_channels_manifest_url']
    chef = ChefThing(script, config)
    register_action(
        'install_chef', chef.dispatch, [],
        ['facts.backends := union(facts.backends, "chef-client")',
         'facts.chef_server_consumed := {chef_server}'],
        {'chef_server': {'type': 'interface',
                         'name': 'chef-server',
                         'required': True},
         'CHEF_SERVER_URL': {'type': 'evaluated',
                             'expression': 'nodes.{chef_server}.'
                             'facts.chef_server_uri'},
         'CHEF_SERVER_PEM': {'type': 'evaluated',
                             'expression': 'nodes.{chef_server}.'
                             'facts.chef_server_pem'},
         'CHEF_SERVER_HOSTNAME': {'type': 'evaluated',
                                  'expression': 'nodes.{chef_server}.name'}},
        timeout=300)
    register_action('run_chef', chef.dispatch, timeout=600)
    register_action('install_chef_server', chef.dispatch, timeout=600)
    register_action('get_chef_info', chef.dispatch)
    register_action('get_cookbook_channels', chef.dispatch)
    register_action(
        'get_latest_channel_version', chef.dispatch, [], [],
        {'channel_name': {'type': 'string',
                          'required': True}})
    register_action(
        'download_cookbooks', chef.dispatch, [], [],
        {'chef_server': {'type': 'interface',
                         'name': 'chef-server',
                         'required': True},
        'CHEF_SERVER_COOKBOOK_CHANNELS': {
            'type': 'evaluated',
            'expression': 'nodes.{chef_server}.'
                          'facts.chef_server_cookbook_channels'}},
        timeout=120)
    register_action('uninstall_chef', chef.dispatch)
    register_action('rollback_install_chef', chef.dispatch)
    register_action('update_cookbooks', chef.dispatch)
    register_action('subscribe_cookbook_channel',
                    chef.dispatch,
                    [],
                    ['facts.chef_server_cookbook_channels := '
                     '"{channel_name}"'],
                    {'channel_name': {'type': 'string',
                                      'required': True}})


def get_environment(required, optional, payload):
    env = dict([(k, v) for k, v in payload.iteritems()
                if k in required + optional])
    for r in required:
        if not r in env:
            return False, {'result_code': 22,
                           'result_str': 'Bad Request (missing %s)' % r,
                           'result_data': None}
    return True, env


def retval(result_code, result_str, result_data):
    return {'result_code': result_code,
            'result_str': result_str,
            'result_data': result_data}


def success(result_str='success', result_data=None):
    return retval(0, result_str, result_data)


class ChefThing(object):
    def __init__(self, script, config):
        self.script = script
        self.config = config

    def install_chef(self, input_data):
        payload = input_data['payload']
        action = input_data['action']
        required = ['CHEF_SERVER_URL', 'CHEF_SERVER_PEM',
                    'CHEF_SERVER_HOSTNAME']
        optional = ['CHEF_RUNLIST', 'CHEF_ENVIRONMENT', 'CHEF_VALIDATION_NAME']
        good, env = get_environment(required, optional, payload)
        if not good:
            return env
        return self.script.run_env('install-chef.sh', env, '')

    def rollback_install_chef(self, input_data):
        return self.uninstall_chef(input_data)

    def uninstall_chef(self, input_data):
        return self.script.run('uninstall-chef.sh')

    def run_chef(self, input_data):
        LOG.info('Running chef')
        payload = input_data['payload']
        action = input_data['action']
        return self.script.run('run-chef.sh')

    def install_chef_server(self, input_data):
        payload = input_data['payload']
        action = input_data['action']
        good, env = get_environment([],
                                    ['CHEF_URL', 'CHEF_WEBUI_PASSWORD'],
                                    payload)
        if not good:
            return env
        return self.script.run_env('install-chef-server.sh', env, '')

    def get_cookbook_channels(self, input_data):
        url = self.config['cookbook_channels_manifest_url']
        manifest = {}

        try:
            content = urllib2.urlopen(url).read()
            manifest = json.loads(content)
        except Exception as e:
            return retval(e.errno, str(e), None)

        return retval(0, 'success', manifest['channels'])

    def get_latest_channel_version(self, input_data):
        payload = input_data['payload']

        channels = {}
        manifest = {}
        channel_name = payload.get('channel_name')
        response = self.get_cookbook_channels(input_data)

        if response['result_code'] == 0:
            channels = response['result_data']

        if channel_name not in channels:
            return retval(100, 'Channel "%s" not available' % channel_name, {})

        url = channels[channel_name]['url']

        try:
            content = urllib2.urlopen(url).read()
            manifest = json.loads(content)
        except Exception as e:
            return retval(e.errno, str(e), None)

        return retval(0, 'success', manifest['current'])

    def subscribe_cookbook_channel(self, input_data):
        payload = input_data['payload']
        action = input_data['action']
        good, env = get_environment([],
                                    ['channel_name'],
                                    payload)
        if not good:
            return env

        channels = []
        channel_name = payload['channel_name']
        response = self.get_cookbook_channels(input_data)

        if response['result_code'] == 0:
            channels = response['result_data'].keys()

        if channel_name in channels:
            return retval(0, 'success', {})
        else:
            return retval(100, 'Channel "%s" not available' % channel_name, {})

    def download_cookbooks(self, input_data):
        payload = input_data['payload']
        action = input_data['action']
        good, env = get_environment(['CHEF_SERVER_COOKBOOK_CHANNELS'],
                                    ['CHEF_REPO_DIR', 'CHEF_REPO',
                                     'CHEF_REPO_BRANCH'],
                                    payload)

        if not good:
            return env

        channels = {}
        channel_name = payload['CHEF_SERVER_COOKBOOK_CHANNELS']
        response = self.get_cookbook_channels(input_data)

        if response['result_code'] == 0:
            channels = response['result_data']

        if channel_name not in channels:
            return retval(100, 'Channel "%s" not available' % channel_name, {})

        url = channels[channel_name]['url']

        try:
            content = urllib2.urlopen(url).read()
            manifest = json.loads(content)
        except Exception as e:
            return retval(e.errno, str(e), None)

        version = manifest['current']
        url = manifest['versions'][version]['url']
        md5 = manifest['versions'][version]['md5']

        env['CHEF_CURRENT_COOKBOOK_VERSION'] = version
        env['CHEF_CURRENT_COOKBOOK_URL'] = url
        env['CHEF_CURRENT_COOKBOOK_MD5'] = md5

        return self.script.run_env('cookbook-download.sh', env, '')

    def update_cookbooks(self, input_data):
        return self.download_cookbooks(input_data)

    def get_chef_info(self, input_data):
        pem = ''
        ipaddr = ''

        try:
            with open('/etc/chef/validation.pem', 'r') as f:
                pem = f.read()
        except IOError as e:
            return retval(e.errno, str(e), None)

        try:
            ipaddr = netifaces.ifaddresses('eth0')[
                netifaces.AF_INET][0]['addr']
        except Exception as e:
            return retval(e.errno, str(e), None)

        return retval(0, 'success',
                      {'validation_pem': pem,
                       'chef_endpoint': 'http://%s:4000' % ipaddr})

    def dispatch(self, input_data):
        self.script.log = LOG
        f = getattr(self, input_data['action'])
        if callable(f):
            return f(input_data)
