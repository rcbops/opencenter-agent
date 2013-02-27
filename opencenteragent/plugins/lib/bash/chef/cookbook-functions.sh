#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Make sure this is a debian derivative
if ! [[ -e /etc/debian_version ]] ; then
    echo "Attempted to run debian derivative script on non-debian distribution" 1>&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

function get_prereqs() {
    apt-get install -y git-core wget
}

function download_cookbooks() {
    # $1 directory to download into
    # $2 cookbook version
    # $3 cookbook tgz url
    # $4 cookbook tgz md5

    local destdir=$1
    local version=$2
    local url=$3
    local md5=$4

    filename=$(basename "$url")
    topdir=$(dirname ${destdir})
    mkdir -p ${topdir}

    pushd ${topdir}

    wget ${url}
    pkg_md5=`md5sum ${filename} | awk '{ print $1 }'`

    if [ "${pkg_md5}" != "${md5}" ]; then
      echo "Downloaded cookbook MD5 '${pkg_md5}' does not match expected MD5 '${md5}'" 1>&2
      exit 1
    fi

    tar -xvzf ${filename}

    if [ -L ${destdir} ]; then
        rm ${destdir}
    elif [ -e ${destdir} ]; then
        echo "${destdir} exists and is not a symlink"
        exit 1
    fi

    ln -s chef-cookbooks-${version} ${destdir}
    popd
}

function checkout_master() {
    # $1 - directory to check out into
    # $2 - repo
    # $3 - branch

    # this will get re-written when we
    # move to the manifest stuff, so I'll
    # just hack this up right now.  --ron

    local destdir=$1
    local repo=$2
    local branch=$3

    local version="2.9.1"

    topdir=$(dirname ${destdir})
    mkdir -p ${topdir}

    pushd ${topdir}

    wget http://j8a8313241d245d72fc52-b3448c2b169a7d986fbb3d4c6b88e559.r9.cf1.rackcdn.com/chef-cookbooks-v${version}.tgz
    tar -xvzf chef-cookbooks-v${version}.tgz

    if [ -L ${destdir} ]; then
        rm ${destdir}
    elif [ -e ${destdir} ]; then
        echo "${destdir} exists and is not a symlink"
        exit 1
    fi

    ln -s chef-cookbooks-v${version} ${destdir}
    popd

    # if [[ ! -e ${destdir} ]]; then
    #     git clone ${repo} ${destdir}
    # fi

    # # directory already exists -- we'll assume it's the same repo
    # pushd ${destdir}
    # git reset --hard
    # git clean -df
    # git checkout ${branch}
    # git pull
    # git clean -df
    # popd
}

function update_submodules() {
    # $1 - base dir

    # local destdir=$1

    # pushd ${destdir}
    # git submodule init
    # git submodule update
    # popd

    return 0
}

function upload_cookbooks() {
    # $1 - base dir
    # $2 - knife-file

    local destdir=$1
    local knife_file=$2

    /opt/chef-server/bin/knife cookbook upload -a -o ${destdir}/cookbooks -c ${knife_file}
}

function upload_roles() {
    # $1 - base dir
    # $2 - knife file

    local destdir=$1
    local knife_file=$2

    /opt/chef-server/bin/knife role from file ${destdir}/roles/*.rb -c ${knife_file}
}
