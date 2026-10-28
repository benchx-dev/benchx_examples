# compare two numpy revisions in one `bx compare`, each built by `spin` in a worktree of its own
#
# usage: ./compare.sh [BASELINE [CONTENDER]]       (tags, branches or commits of $NUMPY)
#
# The provider (provider.py) builds both revisions, and reports each build's
# site-packages directory as the target, so each side of the comparison imports its own
# numpy: there is no PYTHONPATH to set. The environment is activated once, for both.
set -euo pipefail
cd "$(dirname "$0")"

export NUMPY=${NUMPY:-~/repos/numpy}                # a git checkout of numpy; never built in
export WORKTREES=${WORKTREES:-$NUMPY-worktrees}     # where the provider makes one worktree per revision
BASELINE=${1:-v2.4.0}
CONTENDER=${2:-v2.4.3}

# threads, rounds and the revisions profile are in benchx.conf.json
bx compare "@numpy=$BASELINE" "@numpy=$CONTENDER" \
    --suite "$PWD/bench_linalg.py" --run-key "numpy-$BASELINE-vs-$CONTENDER"

# the stored results, one row per side
bx head --table
