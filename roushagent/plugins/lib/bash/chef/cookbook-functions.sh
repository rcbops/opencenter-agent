
# Make sure this is a debian derivative
if ! [[ -e /etc/debian_version ]] ; then
    echo "Attempted to run debian derivative script on non-debian distribution" 1>&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

function get_prereqs() {
    apt-get install -y git-core wget
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

    local version="2.9.0"

    topdir=$(dirname ${destdir})
    mkdir -p ${topdir}

    pushd ${topdir}

    wget http://8a8313241d245d72fc52-b3448c2b169a7d986fbb3d4c6b88e559.r9.cf1.rackcdn.com/chef-cookbooks-v${version}.tgz
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
