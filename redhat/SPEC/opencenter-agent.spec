%define ver 6

Name:       opencenter-agent
Version:    0.1.0
Release:    %{ver}%{?dist}
Summary:	Pluggable, modular host-based agent.

Group:		System
License:	Apache2
URL:		https://github.com/rcbops/opencenter-agent
Source0:	opencenter-agent-%{version}.tgz
Source1:	opencenter-agent.conf
Source2:	opencenter-agent.init

BuildRequires:  python-setuptools
Requires:	python-requests
Requires:	python >= 2.6

BuildArch: noarch

%description
Pluggable, modular host-based agent.  See the output and input
managers for docs on how to write plugins.

%package input-task
Summary: the input task plug-in
Requires: opencenter-agent >= %{version}
Requires: opencenter-client >= %{version}
Requires: python-requests
Group: System

%description
The input-task plugin for OpenCenter

%package output-chef
Summary: an output plugin to run chef tasks
Requires: opencenter-agent >= %{version}
Requires: opencenter-agent-lib-bash >= %{version}
Requires: python-netifaces
Group: System

%description
The Chef plugin for OpenCenter

%package output-packages
Summary: an output plugin to run package tasks
Requires: opencenter-agent >= %{version}
Requires: opencenter-agent-lib-bash >= %{version}
Group: System

%description
The output plugin for OpenCenter

%package lib-bash
Summary: libraries necessary for output tasks to do bash-y things
Requires: opencenter-agent >= %{version}
Group: System

%description
The bash plugin for OpenCenter

%package output-files
Summary: a simple file management plugin.  very very unsafe.
Requires: opencenter-agent >= %{version}
Group: System

%description
The file management pluging for OpenCenter

%package output-adventurator
Summary: an output plugin to run adventures
Requires: opencenter-agent >= %{version}
Requires: opencenter-agent-input-task >= %{version}
Requires: python-opencenter
Group: System

%description
The adventure plugin for OpenCenter

%package output-service
Summary: an output plugin to start/stop/restart services
Requires: opencenter-agent >= %{version}
Group: System

%description
The service plugin for OpenCenter

%package output-openstack
Summary: an output plugin to do openstack-ish things
Requires: opencenter-agent >= %{version}
Requires: opencenter-agent-lib-bash >= %{version}
Group: System

%description
The OpenStack plugin for OpenCenter

%package output-update-actions
Summary: an output plugin to handle restarting a running agent
Requires: opencenter-agent >= %{version}
Group: System

%description
The agent updater plugin for OpenCenter

%prep
%setup -q -n %{name}-%{version}

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build

%install
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/etc/init.d
mkdir -p $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d
install -m 644 $RPM_SOURCE_DIR/conf.d.readme $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d/conf.d.readme
install -m 644 $RPM_SOURCE_DIR/opencenter-agent.conf $RPM_BUILD_ROOT/etc/opencenter-agent.conf
install -m 755 $RPM_SOURCE_DIR/opencenter-agent.init $RPM_BUILD_ROOT/etc/init.d/opencenter-agent
install -m 644 $RPM_SOURCE_DIR/opencenter-agent-endpoints.conf $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d/opencenter-agent-endpoints.conf
install -m 644 $RPM_SOURCE_DIR/opencenter-agent-chef.conf $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d/opencenter-agent-chef.conf
install -m 644 $RPM_SOURCE_DIR/opencenter-agent-packages.conf $RPM_BUILD_ROOT/etc/opencenter/agent.conf.d/opencenter-agent-packages.conf
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT

%files
%config(noreplace) /etc/opencenter-agent.conf
%config(noreplace) /etc/opencenter/agent.conf.d/conf.d.readme
%defattr(-,root,root)
%{python_sitelib}/opencenteragent*
/usr/bin/opencenter-agent.py
/etc/init.d/opencenter-agent
%doc

%files input-task
%config(noreplace) /etc/opencenter/agent.conf.d/opencenter-agent-endpoints.conf
%defattr(-,root,root)
/usr/share/opencenter-agent/plugins/input/task_input.py

%files output-chef
%config(noreplace) /etc/opencenter/agent.conf.d/opencenter-agent-chef.conf
%defattr(-,root,root)
/usr/share/opencenter-agent/plugins/lib/bash/chef/
/usr/share/opencenter-agent/plugins/output/plugin_chef.py

%files output-packages
%config(noreplace) /etc/opencenter/agent.conf.d/opencenter-agent-packages.conf
/usr/share/opencenter-agent/plugins/lib/bash/packages/
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
/usr/share/opencenter-agent/plugins/lib/bash/openstack/
/usr/share/opencenter-agent/plugins/output/plugin_openstack.py

%files output-update-actions
/usr/share/opencenter-agent/plugins/output/plugin_agent_restart.py


%clean
rm -rf $RPM_BUILD_ROOT

%post
chkconfig --add opencenter-agent
chkconfig opencenter-agent on


%changelog
* Mon Sep 10 2012 Joseph W. Breu (joseph.breu@rackspace.com) - 0.1.0
- Initial build
