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

import contextlib
import logging
import os
import shutil
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


@contextlib.contextmanager
def temporary_directory():
    try:
        path = tempfile.mkdtemp(prefix='roush')
        yield path

    finally:
        if os.path.exists(path):
            shutil.rmtree(path)
