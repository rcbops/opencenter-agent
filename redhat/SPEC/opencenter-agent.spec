%define ver 6

Name:       opencenter-agent
Version:    1.0
Release:    %{ver}%{?dist}
Summary:	Pluggable, modular host-based agent.

Group:		System
License:	None
URL:		https://github.com/rpedde/opencenter-agent
Source0:	opencenter-agent-1.0.tgz
Source1:	opencenter-agent.conf
Source2:	opencenter-agent.init

BuildRequires:  python-setuptools
Requires:	python-requests
Requires:	python >= 2.6

BuildArch: noarch


%description
Pluggable, modular host-based agent.  See the output and input
managers for docs on how to write plugins.

%prep
%setup -q -n %{name}-%{version}

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build

%install
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/etc/init.d
install -m 644 $RPM_SOURCE_DIR/opencenter-agent.conf $RPM_BUILD_ROOT/etc/opencenter-agent.conf
install -m 755 $RPM_SOURCE_DIR/opencenter-agent.init $RPM_BUILD_ROOT/etc/init.d/opencenter-agent
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT


%files
%config(noreplace) /etc/opencenter-agent.conf
%defattr(-,root,root)
%{python_sitelib}/opencenteragent*
/usr/share/opencenter-agent/
/usr/bin/opencenter-agent.py
/etc/init.d/opencenter-agent
%doc

%clean
rm -rf $RPM_BUILD_ROOT

%post
chkconfig --add opencenter-agent
chkconfig opencenter-agent on


%changelog
* Mon Sep 10 2012 Joseph W. Breu (joseph.breu@rackspace.com) - 1.0
- Initial build
