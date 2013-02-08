#!/usr/bin/env python

import contextlib
import logging
import os
import sys
import tempfile
import traceback


def detailed_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    full_traceback = repr(
        traceback.format_exception(
            exc_type, exc_value, exc_traceback))

    return full_traceback


@contextlib.contextmanager
def temporary_file():
    try:
        f = tempfile.NamedTemporaryFile(prefix='roush', delete=False)
        f_name = f.name
        f.close()

        yield f_name

    finally:
        if os.path.exists(f_name):
            os.remove(f_name)
