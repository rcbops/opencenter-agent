import os
import string
import subprocess
import logging
from threading import Thread
from Queue import Queue, Empty


def name_mangle(s, prefix=""):
    # we only support upper case variables and as a convenience convert
    # - to _, as - is not valid in bash variables.
    prefix = prefix.upper()
    r = s.upper().replace("-", "_")
    # first character must be _ or alphabet
    if not r[0] == '_' and not (r[0].isalpha() and len(prefix) == 0):
        r = "".join(["_", r])
    # rest of the characters must be alphanumeric or _
    valid = string.digits + string.ascii_uppercase + "_"
    r = "".join([l for l in r if l in valid])
    if len(r) >= 1:
        #valid r, prefix it unless it is already prefixed
        return r if r.find(prefix) == 0 else prefix + r
    raise ValueError("Failed to convert %s to valid bash identifier" % s)


def posix_escape(s):
    #The only special character inside of a ' is ', which terminates
    #the '.  We will surround s with single quotes.  If we encounter a
    #single quote inside of s, we need to close our enclosure with ',
    #escape the single quote in s with "'", then reopen our enclosure
    #with '.
    return "'%s'" % (s.replace("'", "'\"'\"'"))


def find_script(script, script_path):
    for path in script_path:
        filename = os.path.join(path, script)
        #allow directory to be a symlink, but not scripts
        if os.path.exists(filename) and \
           os.path.dirname(os.path.realpath(filename)) == \
           os.path.realpath(path):
           return filename
    return None


class BashScriptRunner(object):
    def __init__(self, script_path=["scripts"], environment=None, log=None):
        self.script_path = script_path
        self.environment = environment or {"PATH":
                                           "/usr/sbin:/usr/bin:/sbin:/bin"}
        self.log = log

    def run(self, script, *args):
        return self.run_env(script, {}, "RCB", *args)

    def run_env(self, script, environment, prefix, *args):
        # first pass: no input, return something like the following
        # { "response": {
        #     "result_code": <result-code-ish>
        #     "result_str": <error-or-success-message>
        #     "result_data": <extended error info or arbitrary data>
        #   }
        # }
        env = {}
        env.update(self.environment)
        env.update(dict([(name_mangle(k, prefix), v)
                         for k, v in environment.iteritems()]))
        response = {"response": {}}
        path = find_script(script, self.script_path)

        if path is None:
            response['result_code'] = 127
            response['result_str'] = "%s not found in %s" % (
                script, ":".join(self.script_path))
            response['result_data'] = {"script": script}
            return response

        to_run = [path] + list(args)
        #first pass, never use bash to run things
        c = subprocess.Popen(to_run,
                             stdin=open("/dev/null", "r"),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env=env)
        if self.log is None:
            response['result_code'] = c.wait()
            response['result_str'] = os.strerror(c.returncode)
            response['result_data'] = {"script": path}
        else:
            response['result_data'] = {"script": path}
            stdout = Queue()
            stderr = Queue()
            stdout_thread = enqueue_output(c.stdout, stdout)
            stderr_thread = enqueue_output(c.stderr, stderr)
            loggers = ((stdout, logging.INFO), (stderr, logging.ERROR))
            while c.poll() is None:
                for out, level in loggers:
                    try:
                        line = out.get(timeout=0.5)
                        self.log.log(level, line.strip())
                    except Empty:
                        pass
            response['result_code'] = c.returncode
            response['result_str'] = os.strerror(c.returncode)
            stdout_thread.join()
            stderr_thread.join()
            for out, level in loggers:
                while not out.empty():
                    line = out.get()
                    self.log.log(level, line.strip())
        return response

def enqueue_output(out, queue):
    def f():
        for line in out:
            queue.put(line)
            out.close()
    t = Thread(target=f)
    t.start()
    return t
