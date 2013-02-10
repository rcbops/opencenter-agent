#!/usr/bin/env python

import fcntl
import getopt
import json
import logging
import logging.config
import os
import signal
import socket
import sys
import time
import traceback

from threading import Thread

from ConfigParser import ConfigParser
from logging.handlers import SysLogHandler

from roushagent import exceptions
from roushagent.modules import OutputManager
from roushagent.modules import InputManager
from roushagent.utils import detailed_exception


class RoushAgentDispatchWorker(Thread):
    def __init__(self, input_handler, output_handler, data):
        super(RoushAgentDispatchWorker, self).__init__()

        self.data = data
        self.output_handler = output_handler
        self.input_handler = input_handler
        self.logger = logging.getLogger('roush-agent.dispatch')

    # apparently signals can only be set in python on the mainline thread.
    # they are already blocked on threads and only handled in mainline.
    #
    # def _worker_signals(self):
    #     signal.signal(signal.SIGTERM, signal.SIG_IGN) # Yay Upstart
    #     signal.signal(signal.SIGINT, signal.SIG_IGN) # Workers should ignore

    def run(self):
        data = self.data
        input_handler = self.input_handler
        output_handler = self.output_handler

#        self._worker_signals()

        data['output'] = {'result_code': 255,
                          'result_str': 'unknown error',
                          'result_data': ''}

        try:
            self.logger.debug('sending input data to output handler')
            data['output'] = output_handler.dispatch(data['input'])
            self.logger.debug('got return from output handler')

        except KeyboardInterrupt:
            raise KeyboardInterrupt

        except Exception as e:
            etext = detailed_exception()
            self.logger.debug('exception in output handler: %s' % etext)
            data['output'] = {'result_code': 254,
                              'result_str': 'dispatch error',
                              'result_data': etext}

        self.logger.debug(
            'passing output handler result back to input handler')
        input_handler.result(data)
        self.logger.debug('dispatch handler terminating')


class RoushAgent():
    def __init__(self, argv, config_section='main'):
        self.base = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                  '..'))
        self.config_section = config_section
        self.input_handler = None
        self.output_handler = None
        self.logger = logging.getLogger()
        self.logger.addHandler(logging.StreamHandler(sys.stderr))
        self.config = {config_section: {}}

        self._initialize(argv, config_section)

    def _initialize(self, argv, config_section):
        # something really screwy with sigint and threading...
        # signal.signal(signal.SIGTERM, lambda a, b: self._exit())
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        try:
            self._setup_scaffolding(argv)
            self._setup_handlers()
        except Exception:
            self._exit(True)

    def _exit(self, exception):
        """Terminate the agent.

        :param: exception: whether an exception should be logged. This should
                           be a boolean value.
        """
        self.logger.debug('exiting...')
        self._cleanup()

        if exception:
            etext = detailed_exception()
            self.logger.error('exception in initializing roush-agent: %s'
                              % etext)

            # wouldn't we rather have a full traceback?
            exc_info = sys.exc_info()
            if hasattr(exc_info[0], '__name__'):
                exc_class, exc, tb = exc_info
                tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                self.logger.error('%s (%s:%s in %s)', exc_info[1], tb_path,
                                  tb_lineno, tb_func)
            else:  # string exception
                self.logger.error(exc_info[0])

            if self.logger.isEnabledFor(logging.DEBUG):
                print ''
                traceback.print_exception(*exc_info)

            sys.exit(1)

        sys.exit(0)

    def _cleanup(self):
        output_handler = self.output_handler
        input_handler = self.input_handler

        if input_handler:
            self.logger.debug('Stopping input handler.')
            try:
                input_handler.stop()
            except:
                pass

        if output_handler:
            self.logger.debug('Stopping output handler.')
            try:
                output_handler.stop()
            except:
                pass

    def _usage(self):
        """Print a usage message."""

        print """The following command line flags are supported:

[-c|--config] <file>: use this config file
[-v|--verbose]:       include if you want verbose logging
[-d|--deamonize]:     if set then roush will run as a daemon"""

    def _parse_opts(self, argv):
        background = debug = False
        configfile = None

        try:
            opts, args = getopt.getopt(argv, 'c:vd',
                                       ['config=', 'verbose', 'daemonize'])
        except getopt.GetoptError as err:
            print str(err)
            self._usage()
            sys.exit(1)

        for o, a in opts:
            if o in ('-c', '--config'):
                configfile = a
            elif o in ('-v', '--verbose'):
                debug = True
            elif o in ('-d', '--daemonize'):
                background = True
            else:
                self._usage()
                sys.exit(1)

        return background, debug, configfile

    def _configure_logs(self, configfile):
        if configfile:
            phandlers = self.logger.handlers
            try:
                self.logger.handlers = []
                logging.config.fileConfig(configfile)
            except:
                self.logger.handlers = phandlers
                self.logger.error("Unable to configure logging")
        self.logger = logging.getLogger()

    def _read_config(self, configfile, defaults=None):
        """Read a configuration file from disk.

        :param: configfile: the path to a configuration file
        :para: defaults:    default configuration values as a dictionary

        :returns: configuration values as a dictionary
        """

        # You can't have a dictionary as a default argument for a method:
        # http://pythonconquerstheuniverse.wordpress.com/category/
        #     python-gotchas/
        if not defaults:
            defaults = {}

        cp = ConfigParser(defaults=defaults)

        if not os.path.exists(configfile):
            raise exceptions.FileNotFound(
                'Configuraton file %s is missing' % configfile)

        cp.read(configfile)
        if not cp.sections():
            raise exceptions.NoConfigFound(
                'The configuration file %s appears to contain no configuration'
                % configfile)

        config = self.config = dict([[s, dict(cp.items(s))]
                                     for s in cp.sections()])
        config_section = self.config_section

        if config_section in config:
            if 'include' in config[config_section]:
                # import and merge a single file
                if not os.path.isfile(config[config_section]['include']):
                    raise RuntimeError(
                        'file %s: include directive %s is not a file' % (
                            configfile,
                            config[config_section]['include']))
                config = self.config = self._read_config(
                    config[config_section]['include'], defaults=config)

            if 'include_dir' in config[config_section]:
                # import and merge a whole directory
                if not os.path.isdir(config[config_section]['include_dir']):
                    raise RuntimeError(
                        'file %s: include_dir directive %s is not a directory'
                        % (configfile,
                           config[config_section]['include_dir']))

                for f in sorted(os.listdir(
                        config[config_section]['include_dir'])):
                    if not f.endswith('.conf'):
                        self.logger.info('Skipping file %s because it does '
                                         'not end in .conf' % f)
                    else:
                        import_file = os.path.join(
                            config[config_section]['include_dir'],
                            f)
                        config = self.config = self._read_config(
                            import_file, defaults=config)

        # merge in the read config into the exisiting config
        for section in config:
            if section in defaults:
                defaults[section].update(config[section])
            else:
                defaults[section] = config[section]

        # pass logging config off to logger
        return defaults

    def _setup_scaffolding(self, argv):
        background, debug, configfile = self._parse_opts(argv)
        print("daemonize: %s, debug: %s, configfile: %s, loglevel: %s" %
              (background, debug, configfile,
               logging.getLevelName(self.logger.getEffectiveLevel())))
        config_section = self.config_section
        config = self.config
        if configfile:
            config = self.config = self._read_config(configfile, defaults={
                'base_dir': self.base})
            self._configure_logs(config[config_section]['log_config'])
        if debug:
            streams = len([h for h in self.logger.handlers
                           if type(h) == logging.StreamHandler])
            if streams == 0:
                self.logger.addHandler(logging.StreamHandler(sys.stderr))
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug('Log level set to debug')

        if background:
            # daemonize
            if os.fork():
                sys.exit(0)
            else:
                os.setsid()
                os.chdir('/')
                os.umask(0)
                if os.fork():
                    sys.exit(0)

            if 'pidfile' in config[config_section]:
                pidfile = open(config[config_section]['pidfile'], 'a+')
                try:
                    fcntl.flock(pidfile.fileno(), fcntl.LOCK_EX |
                                fcntl.LOCK_NB)
                except IOError:
                    self.logger.error('Lock exists on pidfile: already '
                                      'running')
                    pidfile.seek(0)
                    pidfile.truncate()
                    pidfile.write(str(os.getpid()))
                    pidfile.flush()

    def _setup_handlers(self):
        config = self.config
        config_section = self.config_section

        # get directory/path layout
        base_dir = config[config_section].get('base_dir', self.base)

        plugin_dir = config[config_section].get('plugin_dir',
                                                os.path.join(
                                                    base_dir,
                                                    'roushagent/plugins'))
        sys.path.append(os.path.join(plugin_dir, 'lib'))

        # find input and output handlers to load
        default_out = os.path.join(plugin_dir, 'output/plugin_files.py')
        default_in = os.path.join(plugin_dir, 'input/task_input.py')

        output_handlers = config[config_section].get('output_handlers',
                                                     default_out)
        input_handlers = config[config_section].get('input_handlers',
                                                    default_in)

        self.output_handler = OutputManager(
            [x.strip() for x in output_handlers.split(',')], config)
        self.input_handler = InputManager(
            [x.strip() for x in input_handlers.split(',')], config)

    def dispatch(self):
        output_handler = self.output_handler
        input_handler = self.input_handler

        # we'll assume non-blocking.  we should negotiate this
        # with the plugins, I suppose
        do_quit = False
        try:
            while not do_quit:
                self.logger.debug('FETCH')
                result = input_handler.fetch()
                if len(result) == 0:
                    time.sleep(5)
                else:
                    self.logger.debug('Got input from input handler "%s"'
                                      % (result['plugin']))
                    self.logger.debug('Data: %s' % result['input'])

                    # Apply to the pool
                    worker = RoushAgentDispatchWorker(input_handler,
                                                      output_handler,
                                                      result)
                    worker.setDaemon(True)
                    worker.start()
        except KeyboardInterrupt:
            self.logger.debug('Got keyboard interrupt.')
            self._exit(False)

        except Exception, e:
            self.logger.debug('Exception: %s' % detailed_exception())

        self.logger.debug("falling out of dispatch loop")
        self._exit(False)
