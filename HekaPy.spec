%define name heka-py
%define pythonname HekaPy
%define version 0.30.1
%define unmangled_version %{version}
%define release 0

Summary: Heka Python client library
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{pythonname}-%{unmangled_version}.tar.gz
License: MPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{pythonname}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Rob Miller <rmiller@mozilla.com>
Requires:
Obsoletes:

Url: https://github.com/mozilla-services/heka-py

%description
====================
Heka Python Client
====================

Python client library for Mozilla Services' 'Heka' metrics and logging
infrastructure.

%prep
%setup -n %{pythonname}-%{unmangled_version} -n %{pythonname}-%{unmangled_version}

%build
python2.6 setup.py build

%install
python2.6 setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES

%defattr(-,root,root)
