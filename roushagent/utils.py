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
        self.filters = []

    def emit(record):
        parts = record.name.split(".")
        dirs, f = parts[0:-1], parts[-1]
        path = ""
        path += self.path
        for d in dirs:
            path = os.path.join(path, d)
            if not os.path.exists(path):
                os.mkdir(path)
        f = os.path.join(path, f)
        self.stream = open(f, "a")
        logging.StreamHandler.emit(record)
        self.stream.close()
        self.stream = None
