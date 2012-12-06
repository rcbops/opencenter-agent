#!/usr/bin/env python

import sys
import os
from bashscriptrunner import BashScriptRunner

name = 'packages'

def setup(config={}):
    LOG.debug('doing setup for sleep handler')
    if not 'script_path' in config:
        raise ValueError("Expecting script_path in configuration")
    script_path = [config["script_path"]]
    script = BashScriptRunner(script_path=script_path, log=LOG)
    packages = PackageThing(script,config)
    register_action('get_updates', packages.dispatch)
    register_action('do_updates', packages.dispatch)

def get_environment(required, optional, payload):
    env = dict([(k, v) for k, v in payload.iteritems()
                if k in required + optional])
    for r in required:
        if not r in env:
            return False, {'result_code': 22,
                           'result_str': 'Bad Request (missing %s)' % r,
                           'result_data': None}
    return True, env

def retval(result_code, result_str, result_data):
    return {'result_code': result_code,
            'result_str': result_str,
            'result_data': result_data}

class PackageThing(object):
    def __init__(self,script,config):
        self.script=script
        self.config=config

    def do_updates(self,input_data):
        payload = input_data['payload']
        action = input_data['action']
        required = []
        optional = ["PACKAGE_NAME"]
        good, env = get_environment(required, optional, payload)
        if not good:
            return env
        return self.script.run_env("update-package.sh", env, "")

    def get_updates(self,input_data):
	DISTROS = {
		"ubuntu" : "/etc/lsb-release",
		"debian" : "/etc/debian_version",
		"redhat" : "/etc/redhat-release",
	}
        local_distro=None
        for name,location in DISTROS:
            try:
                distroFile=open(location,"r")
                if distroFile:
                    local_distro=name
            except IOError:
                pass
            
        if (local_distro=='debian' or local_distro=='ubuntu'):
            self.get_updatesApt(input_data)
        elif (local_distro=='redhat'):
            self.get_updatesYum(input_data)
        else:
            retval(254,"Package action not supported on this OS","")

    def get_updatesYum(sef,input_data):
        import yum
        action = input_data['action']
        upgrade_list=[]
        skipped_list=[]
        upgrade_count=0
        skipped_count=0
        package_count=0

        yb=yum.YumBase()
        package_count=len(yb.doPackageLists('all').available)
        
        for i in yb.doPackageLists('updates'):
             upgrade_count+=1
             upgrade_list.append(i.name)
        retval(0,"Package Update List",
               {'AvailablePackages': package_count,
                'UpgradablePackageCount': upgrade_count,
                'SkippedPackageCount': skipped_count,
                'UpgradablePackages': upgrade_list,
                'SkippedPackageList': skipped_list })

    def get_updatesApt(self,input_data):
        import apt_pkg
        action = input_data['action']
        upgrade_list=[]
        skipped_list=[]
        upgrade_count=0
        skipped_count=0

        apt_pkg.init()
        cache=apt_pkg.GetCache(None)

        depcache = apt_pkg.GetDepCache(cache)
        depcache.ReadPinFile()
        depcache.Init(None)

        for i in cache.packages:
            if i.current_state is apt_pkg.CURSTATE_INSTALLED:
                if depcache.is_upgradable(i):
                    if depcache.marked_keep(i):
                        skipped_list.append(i.name)
                        skipped_count+=1
                    else:
                        upgrade_list.append(i.name)
                        upgrade_count+=1
        retval(0,"Package Update List",
               {'AvailablePackages': cache.PackageCount,
                'UpgradablePackageCount': upgrade_count,
                'SkippedPackageCount': skipped_count,
                'UpgradablePackages': upgrade_list,
                'SkippedPackageList': skipped_list })

    def dispatch(self, input_data):
        self.script.log = LOG
        f = getattr(self, input_data['action'])
        if callable(f):
            return f(input_data)
