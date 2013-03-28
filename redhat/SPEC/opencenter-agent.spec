%define ver 6

# disable python byte compiling
%global __os_install_post %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

Name:       opencenter-agent
Version:    0.2.0
Release:    %{ver}%{?dist}
Summary:        Pluggable, modular host-based agent.

Group:          System
License:        Apache2
URL:            https://github.com/rcbops/opencenter-agent
Source0:        opencenter-agent-%{version}.tgz
Source1:        opencenter-agent.conf
Source2:        opencenter-agent.upstart
Source3:        conf.d.readme
Source4:        opencenter-agent-endpoints.conf
Source5:        opencenter-agent-chef.conf
Source6:        opencenter-agent-packages.conf
Source7:        log.cfg
Source8:        opencenter-agent.systemd
Source9:        opencenter-agent.sysconfig

BuildRequires:  python-setuptools
Requires:       python-requests
Requires:       python >= 2.6
%if 0%{?rhel} == 6
Requires:       python-sqlalchemy0.7
%else
Requires:       python-sqlalchemy >= 0.7
%endif

BuildArch: noarch

%description
Pluggable, modular host-based agent.  See the output and input
managers for docs on how to write plugins.

%package input-task
Summary: the input task plug-in
Requires: opencenter-agent >= %{version}-%{ver}
Requires: opencenter-client >= %{version}
Requires: python-requests
Group: System

%description input-task
The input-task plugin for OpenCenter

%package output-chef
Summary: an output plugin to run chef tasks
Requires: opencenter-agent >= %{version}-%{ver}
Requires: opencenter-agent-lib-bash >= %{version}-%{ver}
Requires: python-netifaces
Group: System

%description output-chef
The Chef plugin for OpenCenter

%package output-packages
Summary: an output plugin to run package tasks
Requires: opencenter-agent >= %{version}-%{ver}
Requires: opencenter-agent-lib-bash >= %{version}-%{ver}
Group: System

%description output-packages
The output plugin for OpenCenter

%package lib-bash
Summary: libraries necessary for output tasks to do bash-y things
Requires: opencenter-agent >= %{version}-%{ver}
Group: System

%description lib-bash
The bash plugin for OpenCenter

%package output-files
Summary: a simple file management plugin.  very very unsafe.
Requires: opencenter-agent >= %{version}-%{ver}
Group: System

%description output-files
The file management pluging for OpenCenter

%package output-adventurator
Summary: an output plugin to run adventures
Requires: opencenter-agent >= %{version}-%{ver}
Requires: opencenter-agent-input-task >= %{version}-%{ver}
Requires: python-opencenter
Group: System

%description output-adventurator
The adventure plugin for OpenCenter

%package output-service
Summary: an output plugin to start/stop/restart services
Requires: opencenter-agent >= %{version}-%{ver}
Group: System

%description output-service
The service plugin for OpenCenter

%package output-openstack
Summary: an output plugin to do openstack-ish things
Requires: opencenter-agent >= %{version}-%{ver}
Requires: opencenter-agent-lib-bash >= %{version}-%{ver}
Group: System

%description output-openstack
The OpenStack plugin for OpenCenter

%package output-update-actions
Summary: an output plugin to handle restarting a running agent
Requires: opencenter-agent >= %{version}-%{ver}
Group: System

%description output-update-actions
The agent updater plugin for OpenCenter

%prep
%setup -q -n %{name}-%{version}

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} -B setup.py build

%install
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/etc/init
mkdir -p $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d
install -m 644 $RPM_SOURCE_DIR/conf.d.readme $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d/conf.d.readme
install -m 644 $RPM_SOURCE_DIR/log.cfg $RPM_BUILD_ROOT/etc/opencenter/log.cfg
install -m 644 $RPM_SOURCE_DIR/opencenter-agent.conf $RPM_BUILD_ROOT/etc/opencenter/opencenter-agent.conf
%if 0%{?rhel} == 6
install -m 755 $RPM_SOURCE_DIR/opencenter-agent.upstart $RPM_BUILD_ROOT/etc/init/opencenter-agent.conf
%else
mkdir -p $RPM_BUILD_ROOT/etc/sysconfig
mkdir -p $RPM_BUILD_ROOT/etc/systemd/system/
install -m 755 $RPM_SOURCE_DIR/opencenter-agent.sysconfig $RPM_BUILD_ROOT/etc/sysconfig/opencenter-agent
install -m 755 $RPM_SOURCE_DIR/opencenter-agent.systemd $RPM_BUILD_ROOT/etc/systemd/system/opencenter-agent.service
%endif
install -m 644 $RPM_SOURCE_DIR/opencenter-agent-endpoints.conf $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d/opencenter-agent-endpoints.conf
install -m 644 $RPM_SOURCE_DIR/opencenter-agent-chef.conf $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d/opencenter-agent-chef.conf
install -m 644 $RPM_SOURCE_DIR/opencenter-agent-packages.conf $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d/opencenter-agent-packages.conf
%{__python} -B setup.py install --skip-build --root $RPM_BUILD_ROOT
# these things should not get packaged
rm -f $RPM_BUILD_ROOT/usr/share/opencenter-agent/plugins/input/input_example.py
rm -f $RPM_BUILD_ROOT/usr/share/opencenter-agent/plugins/output/plugin_example.py
rm -f $RPM_BUILD_ROOT/usr/share/opencenter-agent/plugins/output/plugin_sleep.py

%files
%config(noreplace) /etc/opencenter/opencenter-agent.conf
%config(noreplace) /etc/opencenter/agent.conf.d/conf.d.readme
%config(noreplace) /etc/opencenter/log.cfg
%defattr(-,root,root)
%{python_sitelib}/opencenteragent*
/usr/bin/opencenter-agent.py
%if 0%{?rhel} == 6
/etc/init/opencenter-agent.conf
%else
%config(noreplace) /etc/sysconfig/opencenter-agent
%config /etc/systemd/system/opencenter-agent.service
%endif
%doc

%files input-task
%config(noreplace) /etc/opencenter/agent.conf.d/opencenter-agent-endpoints.conf
%defattr(-,root,root)
/usr/share/opencenter-agent/plugins/input/task_input.py

%files output-chef
%config(noreplace) /etc/opencenter/agent.conf.d/opencenter-agent-chef.conf
%defattr(-,root,root)
/usr/share/opencenter-agent/plugins/lib/bash/chef/*
/usr/share/opencenter-agent/plugins/output/plugin_chef.py

%files output-packages
%config(noreplace) /etc/opencenter/agent.conf.d/opencenter-agent-packages.conf
/usr/share/opencenter-agent/plugins/lib/bash/packages/*
/usr/share/opencenter-agent/plugins/output/plugin_packages.py

%files lib-bash
/usr/share/opencenter-agent/plugins/lib/bashscriptrunner.py
/usr/share/opencenter-agent/plugins/lib/bash/opencenter.sh

%files output-files
/usr/share/opencenter-agent/plugins/output/plugin_files.py

%files output-adventurator
/usr/share/opencenter-agent/plugins/lib/primitives.py
/usr/share/opencenter-agent/plugins/lib/state.py
/usr/share/opencenter-agent/plugins/output/plugin_adventurator.py

%files output-service
/usr/share/opencenter-agent/plugins/output/plugin_service.py

%files output-openstack
/usr/share/opencenter-agent/plugins/lib/bash/openstack/*
/usr/share/opencenter-agent/plugins/output/plugin_openstack.py

%files output-update-actions
/usr/share/opencenter-agent/plugins/output/plugin_agent_restart.py


%clean
rm -rf $RPM_BUILD_ROOT

%post

# *******************************************************
# ATTENTION: changelog is in reverse chronological order
# *******************************************************
%changelog
* Wed Mar 20 2013 RCB Builder (rcb-deploy@lists.rackspace.com) - 0.2.0
- Fixed Fedora packaging
- Fixed defect with evacuate_hosts (da79833)
- Fixed issue with http_proxy env var being
  passed through to scipts
- Disabled ohai passwd plugin (a408443)
- Making sure curl is installed in setup (046ee33)

* Mon Sep 10 2012 Joseph W. Breu (joseph.breu@rackspace.com) - 0.1.0
- Initial build
