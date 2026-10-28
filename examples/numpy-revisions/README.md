# Demo BenchX user project: comparing two NumPy revisions

Compare two revisions of NumPy in one `bx compare`. Each is built with `spin` in a
worktree of its own, so both builds exist at once. benchx runs the benchmark on them
alternately, round by round, in one session, and says whether the second differs from
the first (the `revisions` profile).

Compared to `numpy-spin`, which benchmarks one build at a time (the full list of
differences is [below](#differences-from-numpy-spin)):

- `bx compare` runs both sides itself, so there is no loop in the script;
- the environment is activated once, for both sides, and there is **no `PYTHONPATH`**:
  the provider reports the directory that holds each build's `numpy`, and pyperf puts
  the target's directory first on `sys.path`, so each side imports its own build.

## Files

- `provider.py`: the target provider. For a revision of `$NUMPY` it makes a git
  worktree under `$WORKTREES`, runs `spin build` in it, and describes the build.
  `prepare` builds (nearly a no-op when nothing changed); `describe` builds nothing.
- `numpy_facts.py`: how a numpy was built (BLAS, LAPACK, C compiler, SIMD). The
  provider declares these facts, and the collector in `benchx.conf.json` checks that
  the benchmark's process sees the same.
- `benchx.conf.json`: the project file: pyperf and its precision, `OPENBLAS_NUM_THREADS=1`
  on both sides, the `revisions` profile with 5 rounds, the provider, the collector.
- `bench_linalg.py`: the benchmark, a matrix product.
- `compare.sh`: the driver. `environment.yml`: an environment to build and run in.

## Running it

You need a git checkout of NumPy (it is never built in; the builds are in worktrees),
and an environment with NumPy's build requirements, `spin`, pyperf and `bx`:

```
$ micromamba create -f environment.yml
$ micromamba activate numpy-revisions
$ pip install -e /path/to/benchx/prototype
```

The benchmark file is recorded as the benchmark's own source, so it must be committed
and unmodified: commit this directory before running. Then:

```
$ NUMPY=~/repos/numpy ./compare.sh v2.4.0 v2.4.3
```

The two revisions are any tags, branches or commits of `$NUMPY`. The first run builds
both (a few minutes each on a many-core machine); later runs reuse the worktrees,
which are named after the revision and its commit, such as `v2.4.0-c5ab79c14c`. They
stay under `$WORKTREES` (by default `$NUMPY-worktrees`); remove one with
`git -C $NUMPY worktree remove`.

## What you should see

```
run numpy-v2.4.0-vs-v2.4.3  profile revisions  baseline edd9d7c22ba2  contender 63d7b31efb1a
  edd9d7c22ba2...: how built: {"blas":{"name":"openblas","version":"0.3.34"},"c_compiler":{"name":"gcc","version":"15.3.0"},...}
  edd9d7c22ba2...: observed env: OPENBLAS_NUM_THREADS=1
  63d7b31efb1a...: how built: {"blas":{"name":"openblas","version":"0.3.34"},"c_compiler":{"name":"gcc","version":"15.3.0"},...}
  63d7b31efb1a...: observed env: OPENBLAS_NUM_THREADS=1

NO CHANGE DETECTED (1)
  bench_matmul                     wall-time  effect   +0.06%  noise   0.30%  rounds=5
```

followed by the stored results, `bx head --table`: five rows for each revision, which
alternate. Both revisions send the matrix product to the same OpenBLAS, so "no change"
is unsurprising. The point is what it was computed from: while this runs, the
benchmark's processes import `v2.4.0-.../build-install/.../numpy` for the baseline and
`v2.4.3-.../build-install/.../numpy` for the contender.

## Differences from `numpy-spin`

| | `numpy-spin` | `numpy-revisions` |
|---|---|---|
| **Goal** | Track a benchmark over a series of revisions (`track.sh`), or vary a setting for one build (`num_threads.sh`), and store each run. | Compare two revisions in one `bx compare` and get a verdict. |
| **Command** | `bx bench @numpy ...`, once per revision or setting. | `bx compare @numpy=A @numpy=B`, with benchx running both sides. |
| **Builds** | One build, in place in `$NUMPY/build-install`. `track.sh` checks out, rebuilds and runs each revision in turn, so two builds never exist at once. | One git worktree per revision under `$WORKTREES`, so both builds exist at once. |
| **Provider** | Builds nothing and ignores the request. It describes the build in `$BUILD` and refuses it if it isn't the checkout's HEAD. | Handles `prepare` and `describe`. It reads the requested revision, creates the worktree, runs `spin build`, and takes a lock. It makes the same HEAD check. |
| **Target path** | The build root, `build-install`. | The `site-packages` directory that holds `numpy`. |
| **Getting numpy imported** | The script exports `PYTHONPATH=$BUILD/usr/lib/python3.12/site-packages/`. That works for one build, but it can't serve two. | No `PYTHONPATH`. The target's directory comes first on `sys.path`, and a stale exported one is harmless. |
| **Collector facts** | `numpy_version`, the full `show_config`, and a summary. Fine for storing results, but the version fails `sides-agree` in a `revisions` comparison. | BLAS, LAPACK, compiler and SIMD only, so the two sides agree if both builds were configured alike. It imports from the working directory instead of relying on `PYTHONPATH`. |
| **Thread setting** | `num_threads.sh` varies `OPENBLAS_NUM_THREADS` across runs, to see its effect. | Fixed at 1 for both sides, in `benchx.conf.json`. The config also sets the `revisions` profile and 5 rounds. |
| **Output** | `bx head --table`: one run per revision. A later `bx compare` cannot pair them: it reads one run, which has to hold both sides, and `track.sh` makes a run per revision. | A verdict (`NO CHANGE DETECTED`, effect and noise) plus the table. |
| **Extras** | The results and the store, in `results/` and `store.parquet`. | `environment.yml`, a `.gitignore` for the results and the store, `compare.sh`, and this README with expected output. |

Shared: the `bench_linalg.py` suite (a copy), the LICENSE, the pyperf adapter and its
precision settings, the project and source URI, and the provider-plus-collector
structure with `verify: how_built`.

## Notes

- **The collector holds no numpy version, on purpose.** benchx matches a collector's
  facts between the two sides of a `revisions` comparison, which may differ in nothing
  but the revision. With the version among the facts (as in `numpy-spin`), comparing
  two different versions fails with `sides-agree`. The facts here are the build configuration, so
  the sides agree only if both builds were configured alike (same BLAS, same compiler,
  same SIMD), which is also worth knowing before trusting a comparison.
- **The target is the `site-packages` directory, not `build-install`.** benchx's tests
  (`test_build_import_path.py`) show on a toy package laid out like a `spin` build that,
  with the build directory as the target and nothing exported, `import` fails in every
  case, and that with one `PYTHONPATH` exported both sides import the build it names,
  without the comparison noticing. Here an exported `PYTHONPATH` is harmless: a run with
  one pointing at the baseline's build still imported each side's own numpy, because the
  target's directory comes first.
- **Python and the build must match.** `python` on the `PATH` runs the benchmark, so it
  must be the Python `spin` built with, here 3.12; the environment provides both.
- **One provider call at a time.** Initializing the submodules of two worktrees at once
  fails on a lock in the shared `.git/config`, so `provider.py` takes a lock. `bx compare`
  prepares its two sides one after the other anyway.
- Tried with Python 3.12, `spin` 0.15, OpenBLAS 0.3.34, GCC 15.3 on Linux.
