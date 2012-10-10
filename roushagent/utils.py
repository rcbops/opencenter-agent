#!/usr/bin/env python

import logging
import os
import sys
import traceback

def detailed_exception(e):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    full_traceback = repr(
        traceback.format_exception(
            exc_type, exc_value, exc_traceback))

    return full_traceback

class SplitFileHandler(logging.StreamHandler):
    def __init__(self, path, encoding=None, delay=0):
        if not os.path.isdir(path):
            raise OSError(2, "Specified path '%s' does not exist or is" + \
                             "not a directory." % (path))
        if not os.access(path, os.W_OK):
            raise OSError(13, "Specified path '%s' is not writable.")
        self.path = path
        self.stream = None
        logging.Handler.__init__(self)

    def emit(self, record):
        parts = record.name.split(".")
        dirs, f = parts[0:-1], parts[-1]
        path = ""
        path += self.path
        for d in dirs:
            path = os.path.join(path, d)
            if not os.path.exists(path):
                os.mkdir(path)
        f = os.path.join(path, f + ".log")
        self.stream = open(f, "a")
        logging.StreamHandler.emit(self, record)
        self.stream.close()
        self.stream = None

class RoushTransLogFilter(logging.Filter):
    def __init__(self, name=""):
        self.name = name
        logging.Filter.__init__(self, name=name)
    def filter(record):
        idx = record.name.find("%s" % self.name)
        if idx == 0:
            return True
        elif idx > 0:
            if record.name[idx - 1] == ".":
                return True
        return False
