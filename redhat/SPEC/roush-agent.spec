Name:		roush-agent
Version:	1.0
Release:	5%{?dist}
Summary:	Pluggable, modular host-based agent.

Group:		System
License:	None
URL:		https://github.com/rpedde/roush-agent
Source0:	roush-agent-1.0.tgz
Source1:	roush-agent.conf
Source2:	roush-agent.init

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
install -m 644 $RPM_SOURCE_DIR/roush-agent.conf $RPM_BUILD_ROOT/etc/roush-agent.conf
install -m 755 $RPM_SOURCE_DIR/roush-agent.init $RPM_BUILD_ROOT/etc/init.d/roush-agent
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT


%files
%config(noreplace) /etc/roush-agent.conf
%defattr(-,root,root)
/usr/lib/python2.6/site-packages/roushagent*
/usr/share/roush-agent/
/usr/bin/roush-agent.py
/etc/init.d/roush-agent
%doc

%clean
rm -rf $RPM_BUILD_ROOT

%post
chkconfig --add roush-agent
chkconfig roush-agent on


%changelog
* Mon Sep 10 2012 Joseph W. Breu (joseph.breu@rackspace.com) - 1.0
- Initial build
