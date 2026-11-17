# numpy-revisions: two NumPy revisions, one of NumPy's own asv benchmarks

This is [UC-03](https://github.com/benchx-dev/benchx/blob/main/docs/use-cases/UC-03-compare.md),
"run a benchmark comparison across two revisions", for NumPy. Two revisions are built with
`spin`, each in a git worktree of its own so both builds exist at once. A benchmark that is
already in NumPy, written in [asv](https://asv.readthedocs.io)'s format, is run on each,
alternately, round by round, and `bx compare` says whether the second revision differs from
the first.

The benchmark is `Mean.time_mean` in NumPy's `benchmarks/benchmarks/bench_function_base.py`,
run unchanged. benchx reads asv's format as a language (discovery, `params`, `setup`) and times it
with pyperf: neither asv nor asv_runner is installed.

```python
class Mean(Benchmark):
    param_names = ['size']
    params = [[1, 10, 100_000]]

    def setup(self, size):
        self.array = np.arange(2 * size).reshape(2, size)

    def time_mean(self, size):
        np.mean(self.array)
```

One benchmark with three sizes is three cases. The file is the same in `v2.4.0` and `v2.4.3`, the
default pair, so both sides run the same benchmark.

## Run it

You need a git checkout of NumPy (it is never built in: the builds are in worktrees next to it),
network access the first time (for NumPy's submodules), and an environment with NumPy's build
requirements, `spin`, pyperf and `bx`:

```
$ micromamba create -f environment.yml
$ micromamba activate numpy-revisions
$ pip install benchx
$ NUMPY=~/repos/numpy ./compare.sh v2.4.0 v2.4.3
```

The two revisions are any tags, branches or commits of `$NUMPY`. The first run builds both (a few
minutes each on a many-core machine); the worktrees, named after the revision and its commit, such
as `v2.4.0-c5ab79c14c`, stay under `$WORKTREES` (by default `$NUMPY-worktrees`), and later runs reuse
them. The measuring took about a minute on a 64-core machine. `ROUNDS=3 ./compare.sh` changes the number of rounds, and
`benchx.conf.json` holds the precision (5 processes x 3 values per case).

Everything that is generated is in `out/`, which is git-ignored; the worktrees are outside this
directory. Remove one with `git -C $NUMPY worktree remove`.

## What `compare.sh` does

1. **Builds both revisions.** For each, a worktree of `$NUMPY` and `spin build` in it. Then it checks
   that `python`, with that build's `site-packages` as `PYTHONPATH`, imports the `numpy` of that
   build, and stops if not.
2. **Alternates the sides.** For each of the 5 rounds, one `bx bench` call per side:

   ```
   PYTHONPATH=<site-packages of the build> bx bench <worktree> --filter 'bench_function_base\.Mean\.time_mean\(' \
       --run-key numpy-v2.4.0-vs-v2.4.3 --round 0 --slot 0 --out out/numpy-v2.4.0-vs-v2.4.3
   ```

   The target is the worktree. `adapter.suite` in `benchx.conf.json`, `benchmarks/benchmarks`, is the
   asv suite inside it, and the worktree's revision is what the result records. `--filter` is asv's
   `--bench`: a regex searched in `name(params)`, so `\(` keeps `time_mean_axis` out. `PYTHONPATH`
   is what makes the benchmark's processes import that revision's build. The calls share a run key;
   `--round` and `--slot` place each one in the alternation, slots counting the calls.
3. **Compares.** `bx compare --run KEY --profile revisions --baseline <commit>`.

## What comes out

The comparison (your numbers will differ):

```
run numpy-v2.4.0-vs-v2.4.3  profile revisions  baseline edd9d7c22ba2  contender 63d7b31efb1a
  differs: benchmark.revision.key
  caveats: baseline: setup-per-call-unbatched, contender: setup-per-call-unbatched

NO CHANGE DETECTED (3)
  bench_function_base.Mean.time_mean [size=1] wall-time  effect   +1.84%  noise   3.47%  rounds=5
  bench_function_base.Mean.time_mean [size=10] wall-time  effect   +0.17%  noise   2.26%  rounds=5
  bench_function_base.Mean.time_mean [size=100000] wall-time  effect   -0.38%  noise   1.15%  rounds=5
```

A case is a change when its effect, the mean relative difference of the paired rounds, is more than
`k` (3) times its noise. These calls take microseconds, so a run to run spread of a few percent is
normal, and a pair of revisions that differ in nothing can show a small "improvement" or
"regression" now and then. `differs: benchmark.revision.key` says that each side's benchmark is the
copy in its own revision. `out/compare.txt` keeps this text and `out/store.parquet` the results (try
`bx head --table`). benchx 0.1.0, from PyPI, prints the three rows without the `[size=...]`.

## Notes

- **`setup-per-call-unbatched`.** `Mean` has a `setup`, so, as in asv_runner >= 0.3.0, every timed call
  sees fresh state: one call per loop, with the setup re-run between calls outside the timer. For a
  call this short that timing includes some timer overhead, and the result is flagged.
- **Why a loop, and not one `bx compare A B`.** With a target of its own, `bx compare` runs both sides
  in one command, as the pyperf adapter does by putting each build first on `sys.path`. The asv
  adapter does not do that yet: it runs the `python` on the `PATH`, and the target only says which
  tree is recorded. So the two builds are selected by `PYTHONPATH`, one `bx bench` call at a time.
  benchx does not record `PYTHONPATH`, which is why step 1 checks it.
- **The suite is each revision's own.** An asv suite outside the checkout being measured does not work
  with `bx bench` yet. Each result records asv's hash of its benchmark's code in its protocol, so a
  benchmark that was edited between the two revisions starts a new series.
- **Skipped module.** `bench_lib.py` imports `asv_runner`, which is not installed, so benchx skips
  that module. The note, and the table of each call, are in `out/bench.log`.
- **Python and the build must match.** `python` on the `PATH` runs the benchmark, so it must be the
  Python `spin` built with, here 3.12; the environment provides both.
- Tried with Python 3.12, `spin` 0.15, OpenBLAS 0.3.34 and GCC 15.3 on Linux, with benchx 0.1.0 and
  with a checkout of benchx.

## What is in this directory

| File | Role |
|---|---|
| `compare.sh` | the driver: builds, the loop, the comparison |
| `benchx.conf.json` | the project file: the asv adapter, its suite and precision, the collector, the `revisions` profile, the paths |
| `numpy_facts.py` | a context collector: how the numpy this Python imports was built (BLAS, LAPACK, compiler, SIMD). benchx matches these facts between the sides, so they agree only if both builds were configured alike. There is no numpy version among them, on purpose: it would differ. |
| `environment.yml` | an environment to build and run in |
