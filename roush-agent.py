#!/usr/bin/env python

import os
import sys
import logging

from modules import PluginManager


if __name__ == "__main__":
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    log.addHandler(logging.StreamHandler(sys.stderr))
    foo = PluginManager("modules/test.py")
