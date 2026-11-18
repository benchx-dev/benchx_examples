#!/usr/bin/env bash
# Compare two numpy revisions on numpy's own asv benchmarks, as `spin bench --compare` does.
# See README.md.
#
#   NUMPY=~/repos/numpy ./compare.sh [-t TEST]... [BASELINE [CONTENDER]]
#
# BASELINE and CONTENDER default to main and the checked-out code. Each is checked out in $NUMPY, which
# must have no uncommitted changes, and built there: a revision in build-<commit>, the checked-out code
# in build. TEST is a regular expression for asv's benchmark names, as spin's -t is; without any,
# every benchmark runs, which takes hours.
set -euo pipefail
cd "$(dirname "$0")"

while getopts t: opt; do [ "$opt" = t ] || exit 2; FILTER=${FILTER:+$FILTER|}$OPTARG; done
shift $((OPTIND - 1))

NUMPY=${NUMPY:-~/repos/numpy}
COMMITS=($(git -C "$NUMPY" rev-parse "${1:-main}^{commit}" "${2:-HEAD}^{commit}" | cut -c1-10))   # before the checkouts move HEAD
BUILDS=(build-${COMMITS[0]} build-${COMMITS[1]})
[ $# -ge 2 ] || BUILDS[1]=build

git -C "$NUMPY" diff --quiet HEAD || { echo "$NUMPY has uncommitted changes" >&2; exit 1; }
START=$(git -C "$NUMPY" symbolic-ref -q --short HEAD || git -C "$NUMPY" rev-parse HEAD)
# A checkout includes the submodules, else a build is made of the wrong sources and benchx tags the tree dirty.
checkout() { git -C "$NUMPY" checkout -q "$1"; git -C "$NUMPY" submodule update --init -q; }
trap 'checkout "$START"' EXIT

for i in 0 1; do
  checkout "${COMMITS[i]}"
  (cd "$NUMPY" && spin build -C "${BUILDS[i]}")
done

# The sides alternate, round by round: each call has its commit checked out, and imports its build,
# the version of which (it has the commit in it) is printed.
rm -rf out
for round in 0 1 2 3 4; do
  for i in 0 1; do
    checkout "${COMMITS[i]}"
    export PYTHONPATH=$(echo "$NUMPY/${BUILDS[i]}"-install/usr/lib/python*/site-packages)
    python -c 'import numpy; print(numpy.__version__, numpy.__file__)'   # which numpy this side measures
    bx bench "$NUMPY" --adapter asv --suite benchmarks/benchmarks ${FILTER:+--filter "$FILTER"} \
      --run-key numpy-revisions --round $round --slot $((2 * round + i))
  done
done

bx compare --run numpy-revisions --baseline "${COMMITS[0]}" --tables
