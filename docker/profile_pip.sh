
# Add pip alias so that --user is automatically passed to install command
function pip() {
    if [[ "$1" == install ]]; then
        /usr/local/bin/pip install --user "${@:2}"
    else
        /usr/local/bin/pip "$@"
    fi
}
