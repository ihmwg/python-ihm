#!/bin/sh
# Build a Debian package from source

set -e

VERSION=$(grep __version__ ../../ihm/__init__.py |cut -d\' -f2)
CODENAME=`lsb_release -c -s`

# Make sure we can find the rest of our input files
TOOL_DIR=`dirname "$0"`
# Get absolute path to top dir
TOP_DIR=`cd "${TOOL_DIR}/../.." && pwd`

ihm_dir_name=`basename ${TOP_DIR}`

cd ${TOP_DIR}
rm -rf debian
cp -r util/debian/ .
rm debian/make-package.sh
sed -i -e "s/\@CODENAME\@/$CODENAME/g" debian/changelog

cd ..
if [ "${ihm_dir_name}" != "python-ihm" ]; then
  mv "${ihm_dir_name}" python-ihm
fi
tar -czf python-ihm_${VERSION}.orig.tar.gz python-ihm
cd python-ihm
dpkg-buildpackage -S
rm -rf ${TOP_DIR}/debian

if [ "${ihm_dir_name}" != "python-ihm" ]; then
  cd ${TOP_DIR}/..
  mv python-ihm "${ihm_dir_name}"
fi
