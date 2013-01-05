
# Make sure this is a debian derivative
if ! [[ -e /etc/debian_version ]] ; then
    echo "Attempted to run debian derivative script on non-debian distribution" 1>&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

function get_prereqs() {
    apt-get install -y git-core
}

function checkout_master() {
    # $1 - directory to check out into
    # $2 - repo
    # $3 - branch

    local destdir=$1
    local repo=$2
    local branch=$3

    if [[ ! -e ${destdir} ]]; then
        git clone ${repo} ${destdir}
    fi

    # directory already exists -- we'll assume it's the same repo
    pushd ${destdir}
    git reset --hard
    git clean -df
    git checkout ${branch}
    git pull
    git clean -df
    popd
}

function update_submodules() {
    # $1 - base dir

    local destdir=$1

    pushd ${destdir}
    git submodule init
    git submodule update
    popd
}

function upload_cookbooks() {
    # $1 - base dir
    # $2 - knife-file

    local destdir=$1
    local knife_file=$2

    knife cookbook upload -a -o ${destdir}/cookbooks -c ${knife_file}
}

function upload_roles() {
    # $1 - base dir
    # $2 - knife file

    local destdir=$1
    local knife_file=$2

    knife role from file ${destdir}/roles/*.rb -c ${knife_file}
}
