#!/usr/bin/env bash
# Compare two numpy revisions on the benchmarks of np_mean_noasv.py: plain pyperf functions, in a file
# outside numpy. The same as compare.sh in all else. See README.md.
#
#   NUMPY=~/repos/numpy ./compare_noasv.sh [-t TEST] [BASELINE [CONTENDER]]
#
# BASELINE and CONTENDER default to main and the checked-out code. Each is checked out in $NUMPY, which
# must have no uncommitted changes, and built there: a revision in build-<commit>, the checked-out code
# in build. TEST is a regular expression for the names of the functions; without it, every bench_*
# function runs.
set -euo pipefail
cd "$(dirname "$0")"
export NUMPY=${NUMPY:-~/repos/numpy}   # provider.py reads it
run_key=numpy-revisions_noasv-$(date +%Y%m%d-%H%M%S)   # every run has a key of its own: the store refuses a key twice

filter=""
while getopts t: option; do
    [ "$option" = t ] || exit 2
    filter=$OPTARG
done
shift $((OPTIND - 1))

# The revisions as short commit ids, before any checkout moves HEAD (^{commit}: a tag is not a commit).
baseline=$(git -C "$NUMPY" rev-parse --short=10 "${1:-main}^{commit}")
contender=$(git -C "$NUMPY" rev-parse --short=10 "${2:-HEAD}^{commit}")
baseline_build=build-$baseline
contender_build=build-$contender
if [ $# -lt 2 ]; then
    contender_build=build   # the checked-out code, where your own `spin build` puts it
fi

if ! git -C "$NUMPY" diff --quiet HEAD; then
    echo "$NUMPY has uncommitted changes: commit them first" >&2
    exit 1
fi

# A checkout includes the submodules: without them a build is made of the wrong sources, and benchx
# tags the tree dirty. The checkout is put back when the script ends.
start=$(git -C "$NUMPY" symbolic-ref --short -q HEAD || git -C "$NUMPY" rev-parse HEAD)
checkout() {
    git -C "$NUMPY" checkout -q "$1"
    git -C "$NUMPY" submodule update --init -q
}
trap 'checkout "$start"' EXIT

checkout "$baseline"
(cd "$NUMPY" && spin build -C "$baseline_build")
checkout "$contender"
(cd "$NUMPY" && spin build -C "$contender_build")

# One side of one round: its commit checked out, its build imported.
measure() {
    local commit=$1 build_dir=$2 round=$3 slot=$4
    checkout "$commit"
    BUILD=$NUMPY/$build_dir-install   # the build directory provider.py reports
    PYTHONPATH=$(ls -d "$BUILD"/usr/lib/python*/site-packages)
    export BUILD PYTHONPATH
    python -c 'import numpy; print(numpy.__version__, numpy.__file__)'   # which numpy this side measures
    bx bench @numpy --adapter pyperf --suite "$PWD/np_mean_noasv.py" --filter "$filter" \
        --run-key "$run_key" --round "$round" --slot "$slot"
}

for round in 0 1 2 3 4; do
    measure "$baseline" "$baseline_build" "$round" $((2 * round))
    measure "$contender" "$contender_build" "$round" $((2 * round + 1))
done

bx compare --run "$run_key" --baseline "$baseline" --tables
