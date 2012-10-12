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
