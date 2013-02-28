#
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

source $OPENCENTER_BASH_DIR/opencenter.sh

id_OS
export DEBIAN_FRONTEND=noninteractive

function get_prereqs() {
    if [[ $OS_TYPE = "debian"  ]] || [[ $OS_TYPE = "ubuntu" ]]; then
        apt-get install -y git-core wget
    else
        yum -y install wget git
    fi
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
