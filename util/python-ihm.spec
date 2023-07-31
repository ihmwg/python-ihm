Name:          python3-ihm
License:       MIT
Group:         Applications/Engineering
Version:       0.38
Release:       1%{?dist}
Summary:       Package for handling IHM mmCIF and BinaryCIF files
Packager:      Ben Webb <ben@salilab.org>
URL:           https://pypi.python.org/pypi/ihm
Source:        ihm-%{version}.tar.gz
BuildRequires: python3-devel, python3-setuptools, gcc

%description
This is a Python package to assist in handling mmCIF and BinaryCIF files
compliant with the integrative/hybrid modeling (IHM) extension. It works
with Python 2.7 or Python 3.

%prep
%setup -n ihm-%{version}

%build
%{__python3} setup.py install --root=${RPM_BUILD_ROOT} --record=INSTALLED_FILES

%files -f INSTALLED_FILES
%defattr(-,root,root)

%changelog
* Mon Jul 31 2023 Ben Webb <ben@salilab.org>   0.38-1
- Update to latest upstream.

* Thu Apr 14 2022 Ben Webb <ben@salilab.org>   0.31-1
- Update to latest upstream.

* Mon Mar 21 2022 Ben Webb <ben@salilab.org>   0.28-1
- Update to latest upstream.

* Thu Jan 27 2022 Ben Webb <ben@salilab.org>   0.27-1
- Update to latest upstream.

* Tue Jan 25 2022 Ben Webb <ben@salilab.org>   0.26-1
- Update to latest upstream.

* Fri Dec 03 2021 Ben Webb <ben@salilab.org>   0.25-1
- Update to latest upstream.

* Fri Jul 09 2021 Ben Webb <ben@salilab.org>   0.20-1
- Initial package.
