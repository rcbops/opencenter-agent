import os
import string
import subprocess
import logging
from threading import Thread
import fcntl
import time

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
        try:
            fh = [h for h in self.log.handlers if hasattr(h, "stream") and
                  h.stream.fileno() > 2][0].stream.fileno()
        except IndexError:
            fh = 2
        #first pass, never use bash to run things
        c = subprocess.Popen(to_run,
                             stdin=open("/dev/null", "r"),
                             stdout=fh,
                             stderr=fh,
                             env=env)
        response['result_data'] = {"script": path}
        c.wait()
        response['result_code'] = c.returncode
        response['result_str'] = os.strerror(c.returncode)
        return response

class WilkExec(object):
    def __init__(self, cmd, stdin=None, stdout=None, stderr=None, env=None):
        self.env = env
        self.pipe_read, self.pipe_write = os.pipe()
        pid = os.fork()
        if pid != 0:
            self.child_pid = pid
            os.close(self.pipe_write)
        else:
            os.close(self.pipe_read)
            if stdin = None:
                f = open("/dev/null", "r")
                stdin = f.fileno()
            os.dup2(stdin, os.sys.stdin.fileno())
            if stdout is not None:
                os.dup2(stdout, os.sys.stdout.fileno())
            if stderr is not None:
                os.dup2(stderr, os.sys.stderr.fileno())
            # FD 3 will be for communicating output variables
            os.dup2(self.pipe_write, 3)
            os.close(self.pipe_write)
            os.execvpe(cmd[0], cmd, env)

    def wait(self, output_variables=None):
        outputs = {}
        ret_code = -1
        running = True
        if output_variables is None:
            output_variables = []
        output_str = ""
        get_outputs = len(output_variables) > 0
        pid, ret_code = os.waitpid(self.child_pid, 0)
        while(True):
            n = os.read(self.pipe_read, 1024)
            output_str += n
            if n == "":
                break
        outputs = dict([
            (k,v) for k,v in [
                line.split("=", 1) for line in
                output_str.strip('\x00').split('\x00')]
            if k in output_variables])
        return ret_code, outputs
