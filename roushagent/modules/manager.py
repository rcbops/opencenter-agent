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

import logging
import os

from functools import partial


# Parent class for the input and output managers


LOG = logging.getLogger('roush.manager')


class Manager(object):
    def __init__(self, path, config={}):
        # Load all available plugins, or those
        # specified by the config.
        self.plugins = {}
        self.loaded_modules = ['modules']
        self.config = config

    def _load_directory(self, path):
        LOG.debug('Preparing to load modules in directory %s' % path)
        dirlist = os.listdir(path)
        for relpath in dirlist:
            p = os.path.join(path, relpath)

            if not os.path.isdir(p) and p.endswith('.py'):
                self._load_file(p)

    def _load_file(self, path):
        shortpath = os.path.basename(path)

        # we can't really load this into the existing namespace --
        # we'll have registration collisions.
        ns = {'global_config': self.config,
              'LOG': LOG}
        LOG.debug('Loading output plugin file %s' % shortpath)
        execfile(path, ns)

        if not 'name' in ns:
            LOG.warning('Plugin missing "name" value. Ignoring.')
            return

        name = ns['name']

        # getChild is only available on python2.7
        # ns['LOG'] = ns['LOG'].getChild('output_%s' % name)
        ns['LOG'] = logging.getLogger('%s.%s' % (ns['LOG'],
                                                 'output_%s' % name))
        ns['register_action'] = partial(self.register_action, name, shortpath)

        self.loaded_modules.append(name)
        self.plugins[name] = ns
        config = self.config.get(name, {})
        ns['module_config'] = config
        if 'setup' in ns:
            ns['setup'](config)
        else:
            LOG.warning('No setup function in %s. Ignoring.' % shortpath)

    def register_action(self, plugin, action, method,
                        constraints=[],
                        consequences=[],
                        args={}):
        pass

    def load(self, path):
        # Load a plugin by file name.  modules with
        # action_foo methods will be auto-registered
        # for the "foo" action
        if type(path) == list:
            for d in path:
                self.load(d)
        else:
            if os.path.isdir(path):
                self._load_directory(path)
            else:
                self._load_file(path)

    def stop(self):
        # Run 'teardown' on all the loaded modules
        for plugin in self.plugins:
            if 'teardown' in self.plugins[plugin]:
                self.plugins[plugin]['teardown']()
