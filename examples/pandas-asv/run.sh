#!/usr/bin/env bash
# One benchmark from pandas' own asv suite, run unchanged by `bx bench PATH --adapter asv` (asv's
# benchmark format, timed by pyperf) under two pandas versions, each in its own venv, alternated
# round by round, then compared. See README.md for what each step shows.
#
# Needs `uv`, git, and an active environment with benchx installed in editable mode from a
# benchx checkout (`pip install -e <checkout>/prototype`). That checkout is installed in both
# venvs; set BENCHX_SRC to the directory with its pyproject.toml to name it instead.
# Everything it creates is here: pandas/, .venv-a, .venv-b and out/ (git-ignored).
# benchx builds nothing, and neither asv nor asv_runner is installed.
set -euo pipefail
cd "$(dirname "$0")"

# Where the venvs get benchx from: the checkout that the active environment's benchx runs from.
BENCHX_SRC=${BENCHX_SRC:-}
if [ -z "$BENCHX_SRC" ]; then
  BENCHX_SRC=$(python -c 'import benchx, pathlib; print(pathlib.Path(benchx.__file__).resolve().parents[1])' 2>/dev/null) || true
fi
if [ -z "$BENCHX_SRC" ] || [ ! -f "$BENCHX_SRC/pyproject.toml" ]; then
  echo "run.sh: cannot find a benchx checkout to install in the venvs." >&2
  echo "  Install benchx in editable mode in the active environment (pip install -e <checkout>/prototype)," >&2
  echo "  or set BENCHX_SRC to the directory with benchx's pyproject.toml." >&2
  exit 1
fi

# The suite is pandas' asv_bench at one tag, the same for both sides: only the installed pandas
# differs. The case is one parameter combination of one benchmark: `str` is object dtype in
# pandas 2.x, and the pyarrow-backed string dtype from pandas 3.0.
PANDAS_REF=v3.1.1
PANDAS_A=2.3.3
PANDAS_B=3.1.1
CASE="strings.Methods.time_lower('str')"
PYTHON_VERSION=3.12
ROUNDS=3   # the fewest that give a verdict
SIDES=("a $PANDAS_A" "b $PANDAS_B")
RUN_KEY=pandas-$(date +%s)
SLOT=0

echo "== 1. fetch pandas' asv suite at $PANDAS_REF (asv_bench/ only)"
if [ "$(git -C pandas describe --tags --exact-match 2>/dev/null)" != "$PANDAS_REF" ]; then
  rm -rf pandas
  git clone -q --depth 1 --branch "$PANDAS_REF" --filter=blob:none --sparse \
      https://github.com/pandas-dev/pandas.git pandas 2>/dev/null
  git -C pandas sparse-checkout set asv_bench
fi
echo "  pandas/asv_bench at $(git -C pandas rev-parse --short HEAD)"

rm -rf out .venv-a .venv-b
mkdir -p out

echo "== 2. the user prepares both environments; benchx builds nothing (benchx from $BENCHX_SRC)"
for SIDE_VERSION in "${SIDES[@]}"; do
  read -r SIDE VERSION <<<"$SIDE_VERSION"
  uv venv -q --python "$PYTHON_VERSION" ".venv-$SIDE"
  uv pip install -q --python ".venv-$SIDE/bin/python" "pandas==$VERSION" pyarrow pyperf -e "$BENCHX_SRC"
  echo "  .venv-$SIDE: pandas $VERSION"
done

echo "== 3. the caller's loop: alternate the sides, round by round, one slot per call"
for ROUND in $(seq 0 $((ROUNDS - 1))); do
  for SIDE_VERSION in "${SIDES[@]}"; do
    read -r SIDE VERSION <<<"$SIDE_VERSION"
    # Activating a venv replaces the one activated before; no deactivate is needed.
    source ".venv-$SIDE/bin/activate"
    # Modules the venv cannot import (no matplotlib, scipy, ...) are listed on stderr and skipped.
    bx bench pandas/asv_bench --adapter asv "$CASE" \
        --run-key "$RUN_KEY" --label "env=pandas-$VERSION" \
        --round "$ROUND" --slot "$SLOT" --out "out/$RUN_KEY" | tee "out/bench-$SLOT.txt"
    echo "  round $ROUND, slot $SLOT: side $SIDE"
    SLOT=$((SLOT + 1))
  done
done

echo "== 4. compare: the sides differ in the pandas the collector read"
bx compare --run "$RUN_KEY" --profile environments --label env \
    --baseline "pandas-$PANDAS_A" | tee out/compare.txt
grep -q 'differs:.*deps\.pandas' out/compare.txt   # the differing fact is shown
if grep -q 'failed invariants' out/compare.txt; then echo "the comparison was refused" >&2; exit 1; fi

echo "== 5. the series: one per environment, each point at the suite's revision"
bx series
