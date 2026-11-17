#!/usr/bin/env bash
# Compare two numpy revisions on one benchmark of numpy's own asv suite, with `bx`.
#
# usage: ./compare.sh [BASELINE [CONTENDER]]      (tags, branches or commits of $NUMPY)
#
# Each revision is built by `spin` in a git worktree of its own, so both builds exist at once.
# The benchmark is numpy's `bench_function_base.Mean.time_mean`, unchanged, from each
# revision's own benchmarks/ directory. The sides alternate round by round, one `bx bench`
# call per side, and `bx compare --run` compares them. See README.md.
set -euo pipefail
cd "$(dirname "$0")"

NUMPY=${NUMPY:-~/repos/numpy}                 # a git checkout of numpy; it is never built in
WORKTREES=${WORKTREES:-$NUMPY-worktrees}      # one worktree per revision, named after it and its commit
BASELINE=${1:-v2.4.0}
CONTENDER=${2:-v2.4.3}
ROUNDS=${ROUNDS:-5}
CASES='bench_function_base\.Mean\.time_mean\('  # a regex, searched in `name(params)`: time_mean(1), ..., not time_mean_axis
RUN_KEY=numpy-$BASELINE-vs-$CONTENDER
unset PYTHONPATH                              # each call below sets its own

# prepare REV: a worktree of $NUMPY at REV, built by `spin`. Sets COMMIT, TREE and SITE.
# `spin build` is incremental, so a worktree that is already built costs almost nothing.
prepare() {
  COMMIT=$(git -C "$NUMPY" rev-parse --verify --quiet "$1^{commit}") || {
    echo "compare.sh: $1 is not a revision of $NUMPY (set NUMPY to a git checkout of numpy)" >&2; exit 1; }
  TREE=$WORKTREES/${1//[^A-Za-z0-9._-]/-}-${COMMIT:0:10}
  if [ ! -d "$TREE" ]; then
    git -C "$NUMPY" worktree add --detach "$TREE" "$COMMIT" >&2
    git -C "$TREE" submodule update --init >&2
  fi
  (cd "$TREE" && spin build) >&2
  # The directory that holds the built `numpy` package: what the benchmark must import from.
  SITE=$(dirname "$(ls -d "$TREE"/build-install/usr/lib/python3*/site-packages/numpy | head -n 1)")
  # benchx does not record PYTHONPATH, so check here that this side imports its own build.
  local imported
  imported=$(PYTHONPATH=$SITE python -c 'import numpy; print(numpy.__file__)')
  case $imported in
    "$TREE"/build-install/*) echo "  $1: $imported" ;;
    *) echo "compare.sh: with PYTHONPATH=$SITE, python imports $imported, not the build of $1" >&2; exit 1 ;;
  esac
}

echo "== 1. build both revisions with spin, each in its own worktree"
mkdir -p "$WORKTREES"
prepare "$BASELINE";  BASE_COMMIT=$COMMIT; BASE_TREE=$TREE; BASE_SITE=$SITE
prepare "$CONTENDER"; CONT_TREE=$TREE; CONT_SITE=$SITE

echo "== 2. alternate the sides, round by round: one bx bench call per side and round"
rm -rf out; mkdir -p out
# bx bench prints a table and some notes for every call; they go to out/bench.log, shown if a call fails.
side() {  # side TREE SITE ROUND SLOT: one bx bench call
  # PYTHONPATH selects the numpy that the benchmark imports. The target is the worktree: its
  # benchmarks/benchmarks directory (adapter.suite) holds the suite, and its revision is recorded.
  PYTHONPATH=$2 bx bench "$1" --filter "$CASES" --run-key "$RUN_KEY" --round "$3" --slot "$4" \
      --out "out/$RUN_KEY" >> out/bench.log 2>&1 || { tail -n 30 out/bench.log >&2; exit 1; }
}
for ROUND in $(seq 0 $((ROUNDS - 1))); do
  side "$BASE_TREE" "$BASE_SITE" "$ROUND" $((2 * ROUND))
  side "$CONT_TREE" "$CONT_SITE" "$ROUND" $((2 * ROUND + 1))
  echo "  round $ROUND: $BASELINE, then $CONTENDER"
done

echo "== 3. compare: the revisions profile; the baseline is named by its commit"
bx compare --run "$RUN_KEY" --profile revisions --baseline "${BASE_COMMIT:0:10}" | tee out/compare.txt
