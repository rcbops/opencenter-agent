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

import json
import os
import subprocess
import sys
import time

from bashscriptrunner import BashScriptRunner
from opencenterclient.client import OpenCenterEndpoint

name = 'packages'


def setup(config={}):
    LOG.debug('doing setup for packages handler')
    if not 'bash_path' in global_config['main']:
        LOG.error("bash_path not configured")
        raise ValueError("Expecting bash_path in configuration")
    script_path = [os.path.join(global_config['main']['bash_path'], name)]
    env = {"OPENCENTER_BASH_DIR": global_config['main']['bash_path']}
    script = BashScriptRunner(script_path=script_path, log=LOG,
                              environment=env)
    packages = PackageThing(script, config)
    register_action('get_updates', packages.dispatch, timeout=300)  # 5 min
    register_action('do_updates', packages.dispatch, timeout=600)   # 10 min
    register_action('upgrade_agent', packages.dispatch, timeout=300)  # 5 min


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
    print "retval: returning %d %s %s" % (result_code, result_str, result_data)
    return {'result_code': result_code,
            'result_str': result_str,
            'result_data': result_data}


class PackageThing(object):
    def __init__(self, script, config):
        self.script = script
        self.config = config
        self.pidfile = '/var/run/opencenter-agent.pid'

    def _return(self, result_code, result_str, result_data=None):
        if result_data is None:
            result_data = {}
        return {'result_code': result_code,
                'result_str': result_str,
                'result_data': result_data}

    def _success(self, result_str='success', result_data=None):
        if result_data is None:
            result_data = {}
        return self._return(0, result_str, result_data)

    def _failure(self, result_str='fail', result_data=None):
        if result_data is None:
            result_data = {}
        return self._return(1, result_str, result_data)

    def _update_task(self, result):
        task_id = input_data['id']
        endpoint_url = global_config['endpoints']['admin']
        ep = OpenCenterEndpoint(endpoint_url)
        task = ep.tasks[task_id]
        task._request_get()
        task.state = 'done'
        task.result = result
        task.save()

    def do_updates(self, input_data):
        """
        Supported payload options:

        :PACKAGE_NAME: - this will update a specific package
        :SLEEP: - the task will sleep for this many seconds before exiting
        :DISABLE_RESTART: - disables auto-restart on package install
        """
        payload = input_data['payload']
        # action = input_data['action']
        required = []
        optional = ["PACKAGE_NAME", "SLEEP", "DISABLE_RESTART"]

        if 'SLEEP' in payload:
            sleep = payload['SLEEP']

        good, env = get_environment(required, optional, payload)

        if sleep:
            time.sleep(int(sleep))

        if not good:
            return env
        return self.script.run_env("update-package.sh", env, "")

    def upgrade_agent(self, input_data):
        """Upgrades a running opencenter-agent, from packages"""
        pid = os.fork()
        if pid != 0:
            # Parent
            LOG.info('**** Upgrading agent')
            self.do_updates(input_data)
        else:
            # child
            ppid = os.getppid()
            timer = 60  # check parent state for 60s then timeout
            error = False  # initialize error state as False
            alive = True
            count = 0
            while alive:
                time.sleep(1)
                try:
                    os.kill(ppid, 0)
                except OSError:
                    alive = False
                count += 1
                if count > timer:
                    error = True
                    break
            if error:
                LOG.info('**** FAILED due to timeout')
                # need to throw an error back at the task
                result = self._failure()
                self._update_task(result)
            else:
                exists = os.path.isfile(self.pidfile)
                if exists:
                    f = open(self.pidfile, 'r')
                    new_pid = int(f.read())
                    f.close()
                    if new_pid == ppid:
                        LOG.info('**** FAILED pid did not change')
                        # pidfile contains same pid as my parent pid
                        result = self._failure()
                        self._update_task(result)
                    else:
                        LOG.info('**** SUCCESS pid changed')
                        # pidfile contains different pid than my parent pid
                        result = self._success()
                        self._update_task(result)
                else:
                    LOG.info('**** FAILED pidfile does not exist')
                    result = self._failure()
                    self._update_task(result)

    def get_updates(self, input_data):
        DISTROS = {
            "ubuntu": "/etc/lsb-release",
            "debian": "/etc/debian_version",
            "redhat": "/etc/redhat-release",
        }
        local_distro = None
        for name in DISTROS:
            try:
                distroFile = open(DISTROS[name], "r")
                if distroFile:
                    local_distro = name
            except IOError:
                pass

        if (local_distro == 'debian' or local_distro == 'ubuntu'):
            return self.get_updatesApt(input_data)
        elif (local_distro == 'redhat'):
            return self.get_updatesYum(input_data)
        else:
            return retval(254, "Package action not supported on this OS", {})

    def get_updatesYum(sef, input_data):
        import yum
        action = input_data['action']
        upgrade_list = []
        skipped_list = []
        upgrade_count = 0
        skipped_count = 0
        package_count = 0

        yb = yum.YumBase()
        package_count = len(yb.doPackageLists('all').available)
        print "package_count = %d" % package_count

        for i in yb.doPackageLists('updates'):
            print "update package %s" % i
            upgrade_count += 1
            upgrade_list.append(i.name)
        return(retval(0, "Package Update List", {
            "consequences": [
                'attrs.AvailablePackages := %s' % package_count,
                'attrs.UpgradablePackageCount := %s' % upgrade_count,
                'attrs.SkippedPackageCount := %s' % skipped_count,
                'attrs.UpgradablePackages := %s' % json.dumps(upgrade_list),
                'attrs.SkippedPackageList := %s' % json.dumps(skipped_list)]}))

    def get_updatesApt(self, input_data):
        import apt_pkg
        action = input_data['action']
        upgrade_list = []
        skipped_list = []
        upgrade_count = 0
        skipped_count = 0

        apt_pkg.init()

        if os.path.exists("/etc/apt/apt.conf"):
            apt_pkg.read_config_file(apt_pkg.config,
                                     "/etc/apt/apt.conf")
        if os.path.isdir("/etc/apt/apt.conf.d"):
            apt_pkg.read_config_dir(apt_pkg.config,
                                    "/etc/apt/apt.conf.d")
        apt_pkg.init_system()

        cache = apt_pkg.GetCache(None)

        depcache = apt_pkg.GetDepCache(cache)
        depcache.ReadPinFile()
        depcache.Init(None)

        for i in cache.packages:
            if i.current_state is apt_pkg.CURSTATE_INSTALLED:
                if depcache.is_upgradable(i):
                    if depcache.marked_keep(i):
                        skipped_list.append(i.name)
                        skipped_count += 1
                    else:
                        upgrade_list.append(i.name)
                        upgrade_count += 1
        return(retval(0, "Package Update List", {
            "consequences": [
                'attrs.AvailablePackages := %s' % cache.PackageCount,
                'attrs.UpgradablePackageCount := %s' % upgrade_count,
                'attrs.SkippedPackageCount := %s' % skipped_count,
                'attrs.UpgradablePackages := %s' % json.dumps(upgrade_list),
                'attrs.SkippedPackageList := %s' % json.dumps(skipped_list)]}))

    def dispatch(self, input_data):
        self.script.log = LOG
        f = getattr(self, input_data['action'])
        if callable(f):
            return f(input_data)
