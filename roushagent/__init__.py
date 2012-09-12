#!/usr/bin/env python

import fcntl
import getopt
import json
import logging
import os
import signal
import socket
import sys
import time
import traceback

from ConfigParser import ConfigParser
from logging.handlers import SysLogHandler

from roushagent.modules import OutputManager
from roushagent.modules import InputManager


input_handler = None
log = logging.getLogger()


def _do_exit():
    global input_handler
    global log

    if input_handler:
        log.debug("Stopping input handler.")
        input_handler.stop()
    log.debug("Bailing")
    sys.exit(0)


def main(argv):
    signal.signal(signal.SIGTERM, lambda a, b: _do_exit())

    try:
        _main(argv)
    except KeyboardInterrupt:
        _do_exit()
    except SystemExit:
        raise
    except:
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
            log.error("%s (%s:%s in %s)", exc_info[1], tb_path,
                      tb_lineno, tb_func)
        else:  # string exception
            log.error(exc_info[0])
        if log.isEnabledFor(logging.DEBUG):
            print ''
            traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)


def _read_config(configfile, defaults={}):
    cp = ConfigParser(defaults=defaults)
    cp.read(configfile)
    config = dict([[s, dict(cp.items(s))] for s in cp.sections()])

    if 'main' in config:
        if 'include' in config['main']:
            # import and merge a single file
            if not os.path.isfile(config['main']['include']):
                raise RuntimeError(
                    'file %s: include directive %s is not a file' % (
                        configfile,
                        config['main']['include'],))

            config = _read_config(config['main']['include'])

        if 'include_dir' in config['main']:
            # import and merge a whole directory
            if not os.path.isdir(config['main']['include_dir']):
                raise RuntimeError(
                    'file %s: include_dir directive %s is not a dir' % (
                        configfile,
                        config['main']['include_dir'],))

            for d in sorted(os.listdir(config['main']['include_dir'])):
                import_file = os.path.join(config['main']['include_dir'], d)

                config = _read_config(import_file, config)

    # merge in the read config into the exisiting config
    for section in config:
        if section in defaults:
            defaults[section].update(config[section])
        else:
            defaults[section] = config[section]

    print defaults
    return defaults


def _main(argv):
    global input_handler
    global log

    background = False
    debug = False
    configfile = None
    pidfile = None
    config = {"main": {}}

    def daemonize():
        if os.fork():
            sys.exit(0)
        else:
            os.setsid()
            os.chdir('/')
            os.umask(0)
            if os.fork():
                sys.exit(0)

    try:
        opts, args = getopt.getopt(argv, 'c:vd')
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(1)

    for o, a in opts:
        if o == '-c':
            configfile = a
        elif o == '-v':
            debug = True
        elif o == '-d':
            background = True
        else:
            usage()
            sys.exit(1)

    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.WARNING)

    if configfile:
        base = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
        config = _read_config(configfile, defaults={'base_dir': base})

    if background:
        logdev = config['main'].get('syslog_dev', '/dev/log')

        log.addHandler(SysLogHandler(address=logdev))
        daemonize()

        if 'pidfile' in config['main']:
            pidfile = open(config['main']['pidfile'], 'a+')
            try:
                fcntl.flock(pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                log.error('Lock exists on pidfile: already running')
            pidfile.seek(0)
            pidfile.truncate()
            pidfile.write(str(os.getpid()))
            pidfile.flush()

    else:
        log.addHandler(logging.StreamHandler(sys.stderr))

    # get directory/path layout
    base_dir = config['main'].get('base_dir', '../')

    plugin_dir = config['main'].get('plugin_dir',
                                    os.path.join(base_dir,
                                                 'roushagent/plugins'))
    sys.path.append(os.path.join(plugin_dir, 'lib'))

    # find input and output handlers to load
    default_out = os.path.join(plugin_dir, 'output/plugin_files.py')
    default_in = os.path.join(plugin_dir, 'input/task_input.py')

    output_handlers = config['main'].get('output_handlers', default_out)
    input_handlers = config['main'].get('input_handlers', default_in)

    output_handler = OutputManager(
        [x.strip() for x in output_handlers.split(',')], config)
    input_handler = InputManager(
        [x.strip() for x in input_handlers.split(',')], config)

    # we'll assume non-blocking.  we should negotiate this
    # with the plugins, I suppose
    do_quit = False

    while not do_quit:
        result = input_handler.fetch()
        if len(result) == 0:
            time.sleep(5)
        else:
            log.debug('Got input from input handler "%s"' %
                      result['plugin'])
            log.debug('Data: %s' % result['input'])

            result['output'] = {'result_code': 255,
                                'result_str': 'unknown error',
                                'result_data': ''}

            try:
                result['output'] = output_handler.dispatch(result['input'])

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                full_traceback = repr(
                    traceback.format_exception(
                        exc_type, exc_value, exc_traceback))

                result['output'] = {'result_code': 254,
                                    'result_str': 'dispatch error',
                                    'result_data': full_traceback}
                print full_traceback
                log.warn(full_traceback)

            input_handler.result(result)
