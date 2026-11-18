#!/usr/bin/env bash
# One benchmark from pandas' own asv suite, run unchanged by `bx bench PATH --adapter asv` (asv's
# benchmark format, timed by pyperf) under two pandas versions, each in its own venv, alternated
# round by round, then compared. See README.md for what each step shows.
#
# Needs `uv` and git. Both venvs get the benchx of the active environment: its checkout if it is
# an editable install, else the same version from PyPI (the latest if there is none). Set
# BENCHX_SRC to a benchx checkout (the directory with its pyproject.toml) to install that instead.
# Everything it creates is here: pandas/, .venv-a, .venv-b and out/ (git-ignored).
# benchx builds nothing, and neither asv nor asv_runner is installed.
set -euo pipefail
cd "$(dirname "$0")"

# Where the venvs get benchx from: BENCHX_SRC, else the checkout of an editable benchx in the
# active environment, else PyPI, at the active environment's version if it has one.
BENCHX_SRC=${BENCHX_SRC:-}
if [ -z "$BENCHX_SRC" ]; then
  BENCHX_SRC=$(python - 2>/dev/null <<'EOF' || true
import importlib.metadata as md, json, urllib.parse
url = {}
for name in ("benchx", "benchx-prototype"):  # older checkouts install benchx-prototype
    try:
        url = json.loads(md.distribution(name).read_text("direct_url.json") or "{}")
        break
    except md.PackageNotFoundError:
        pass
if url.get("dir_info", {}).get("editable"):
    print(urllib.parse.unquote(urllib.parse.urlparse(url["url"]).path))
EOF
)
fi
if [ -n "$BENCHX_SRC" ]; then
  BENCHX_REQ=(-e "$BENCHX_SRC")
else
  BENCHX_VERSION=$(python -c 'import importlib.metadata as m; print(m.version("benchx"))' 2>/dev/null || true)
  BENCHX_REQ=("benchx${BENCHX_VERSION:+==$BENCHX_VERSION}")
fi

# The store is out/store.parquet (benchx.conf.json). $BENCHX_HOME would relocate it, and mix
# this run's series with whatever else is stored there.
unset BENCHX_HOME

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

echo "== 2. the user prepares both environments; benchx builds nothing (benchx: ${BENCHX_REQ[*]})"
for SIDE_VERSION in "${SIDES[@]}"; do
  read -r SIDE VERSION <<<"$SIDE_VERSION"
  uv venv -q --python "$PYTHON_VERSION" ".venv-$SIDE"
  uv pip install -q --python ".venv-$SIDE/bin/python" "pandas==$VERSION" pyarrow pyperf "${BENCHX_REQ[@]}"
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
if grep -q 'failed invariants' out/compare.txt; then echo "run.sh: the comparison was refused" >&2; exit 1; fi
if ! grep -q 'differs:.*deps\.pandas' out/compare.txt; then   # the differing fact is shown
  echo "run.sh: the comparison does not name deps.pandas as differing" >&2; exit 1
fi

echo "== 5. the series: one per environment, each point at the suite's revision"
bx series
