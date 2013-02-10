#!/usr/bin/env python

import os

# Parent class for the input and output managers

class Manager(object):
    def _load_directory(self, path):
        LOG.debug('Preparing to load modules in directory %s' % path)
        dirlist = os.listdir(path)
        for relpath in dirlist:
            p = os.path.join(path, relpath)

            if not os.path.isdir(p) and p.endswith('.py'):
                self._load_file(p)

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
