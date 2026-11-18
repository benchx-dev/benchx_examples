# numpy-revisions: two NumPy revisions, one of NumPy's own asv benchmarks

This is [UC-03](https://github.com/benchx-dev/benchx/blob/main/docs/use-cases/UC-03-compare.md),
"run a benchmark comparison across two revisions", for NumPy. Two revisions are built with
`spin`, each in a build directory of its own in the NumPy checkout, so both builds exist at once.
A benchmark that is already in NumPy, written in [asv](https://asv.readthedocs.io)'s format, is
run on each, alternately, round by round, and `bx compare` says whether the second revision
differs from the first.

`compare.sh` is used like `spin bench --compare`: two revisions, and `-t` to choose benchmarks of
NumPy's own asv suite, `benchmarks/benchmarks`, which are run unchanged. The example below is
`Mean.time_mean`, in `bench_function_base.py`. benchx reads asv's format as a language (discovery,
`params`, `setup`) and times it with pyperf: neither asv nor asv_runner is installed.

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
pair used below, so both sides run the same benchmark.

## Run it

You need a git checkout of NumPy with no uncommitted changes (the revisions are checked out in it,
see below), network access the first time (for NumPy's submodules), and an environment with NumPy's
build requirements, `spin`, pyperf and `bx`:

```
$ micromamba create -f environment.yml
$ micromamba activate numpy-revisions
$ pip install benchx
$ NUMPY=~/repos/numpy ./compare.sh -t 'Mean\.time_mean\(' v2.4.0 v2.4.3
```

The usage is `./compare.sh [-t TEST]... [BASELINE [CONTENDER]]`, and everything is optional, as it is
for `spin bench --compare`:

- **Revisions.** Anything that git resolves in `$NUMPY`: tags, branches, `HEAD`, `HEAD^`, commits. They
  default to `main` and the checked-out code, and `./compare.sh v2.4.0` compares `v2.4.0` with it. The
  first is the baseline and the second the contender.
- **`-t TEST`.** A regular expression searched in asv's name of a benchmark, `file.Class.method`
  (the file is under `benchmarks/benchmarks/`, without `.py`), and in `name(params)` for each parameter
  combination, as `spin bench -t` does. So `-t bench_function_base` is a file, `-t Mean` a class, and
  `-t Mean.time_mean` a method, and also `time_mean_axis`, since it only searches. The `\(` above ends the
  name, so that only `time_mean` is selected. Give `-t` more than once to select more. Without `-t`
  every benchmark runs, which takes hours. A `-t` that selects nothing is refused, and the refusal lists
  the benchmarks whose names are closest to it (a misspelled class or method finds its benchmarks), or the first few that exist.

**One combination of parameters.** A parametrized benchmark is searched once per combination, as
`name(p0, p1, ...)`: the arguments in the order of its `param_names`, each as its Python `repr`, so a string
is quoted and a tuple keeps its parentheses. `Partition.time_argpartition` takes `dtype, array_type, k`, so
this selects one case of it, the same in `v2.4.0` and `v2.4.3`:

```
$ NUMPY=~/repos/numpy ./compare.sh -t "Partition\.time_argpartition\('int16', \('sorted_block', 1000\), 10\)" v2.4.0 v2.4.3
```

The parentheses are escaped because the filter is a regular expression, and the double quotes keep the shell
from reading the single ones. The arguments in another order select nothing. When a `-t` names a
parametrized benchmark and none of its combinations, the refusal says so, gives the order of the parameters
and one case as it is searched:
`bench_function_base.Partition.time_argpartition(dtype, array_type, k) is searched as
bench_function_base.Partition.time_argpartition('float64', ('random',), 10)`.

**Builds.** `spin build` builds each revision in `$NUMPY`, in a build directory of its own, so both builds
exist at once: a revision in `build-<commit>` (installed in `build-<commit>-install`), the checked-out
code in `build`, where your own `spin build` puts it. It runs every time, and is incremental: a revision
takes a few minutes the first time on a many-core machine, and less after. NumPy git-ignores these
directories. `<commit>` is the short id (10 hex digits) of the commit the revision names now, so `main` is built in
the directory of the commit `main` is at (`build-c5ab79c14c` for `v2.4.0`).

| You run | Baseline | Contender |
|---|---|---|
| `./compare.sh` | `main`, built in `build-<commit>` | the checked-out code, built in `build` |
| `./compare.sh SHA1` | `SHA1`, built in `build-<SHA1>` | the checked-out code, built in `build` |
| `./compare.sh SHA1 SHA2` | `SHA1`, built in `build-<SHA1>` | `SHA2`, built in `build-<SHA2>` |

**The checkout.** `bx` measures the tree it is given, and tells the sides apart by their trees, so each
call has its commit checked out first: ten checkouts for 5 rounds. A checkout includes NumPy's
submodules (`git submodule update --init`): releases pin other commits of `vendored-meson`, `svml` and
others than `main` does, and without the update a build is made of the wrong sources and benchx tags the
tree dirty. When the script ends, also when it fails or is interrupted, the checkout is
put back, on its branch or at its commit. That is why it refuses to start when `$NUMPY` has
uncommitted changes, which would otherwise go into a build: commit them first. Untracked files are left
alone. Checking out another revision touches the files that differ, so your next `spin build` in
`$NUMPY` recompiles those.

The measuring took about a minute on a 64-core machine. `benchx.conf.json` holds the precision
(5 processes x 3 values per case), and the loop in `compare.sh` the number of rounds (5).

Everything that is generated here is in `out/`, which is git-ignored.

## What `compare.sh` does

1. **Builds both revisions.** Each is resolved to a commit with `git rev-parse` before any checkout moves
   `HEAD` (`bx compare` takes a commit id, and a tag is not one: `^{commit}`). For each, the checkout of
   the commit and `spin build -C build-<commit>`, or `spin build -C build` for the checked-out code.
2. **Alternates the sides.** For each of the 5 rounds, one `bx bench` call per side, after checking out
   its commit and printing which numpy it imports (version and path):

   ```
   PYTHONPATH=<site-packages of the build> bx bench $NUMPY --adapter asv --suite benchmarks/benchmarks \
       --filter 'Mean\.time_mean\(' --run-key numpy-revisions --round 0 --slot 0
   ```

   The target is the checkout, `--suite` is the asv suite inside it, and the checkout's revision is what
   the result records. `--adapter asv` and `--suite` are in the script: the `adapter` block of
   `benchx.conf.json` names pyperf and holds only the timing, and asv, which is timed by pyperf, takes
   it too, so the same file serves a pyperf suite. `--filter` is asv's `--bench`, the `-t` options
   joined by `|` (without `-t` there is none). `PYTHONPATH` is what makes
   the benchmark's processes import that revision's build. The calls share a run key; `--round` and
   `--slot` place each one in the alternation, slots counting the calls.
3. **Compares.** `bx compare --run numpy-revisions --baseline <commit> --tables`; `compare.profile` in
   `benchx.conf.json` makes it the `revisions` profile, and `--tables` adds what `spin bench --compare`
   prints: a table of each commit, then one of the changes (only the changed rows). Then the checkout is
   put back.

## What comes out

The comparison (your numbers will differ):

```
run numpy-revisions  profile revisions  baseline edd9d7c22ba2  contender 63d7b31efb1a
  differs: benchmark.revision.key
  caveats: baseline: setup-per-call-unbatched, contender: setup-per-call-unbatched

NO CHANGE DETECTED (3)
  bench_function_base.Mean.time_mean [size=1] wall-time  effect   -0.18%  noise   0.97%  rounds=5
  bench_function_base.Mean.time_mean [size=10] wall-time  effect   -0.24%  noise   0.79%  rounds=5
  bench_function_base.Mean.time_mean [size=100000] wall-time  effect   +0.88%  noise   0.83%  rounds=5

For numpy commit c5ab79c1 (5 rounds):
bench_function_base.Mean.time_mean  ok
  ======== ============
    size               
  -------- ------------
     1      8.26±0.2μs 
     10     8.33±0.1μs 
   100000    162±2μs   
  ======== ============

For numpy commit 8bcb2e72 (5 rounds):
bench_function_base.Mean.time_mean  ok
  ======== =============
    size                
  -------- -------------
     1      8.26±0.09μs 
     10     8.41±0.09μs 
   100000     164±2μs   
  ======== =============

No benchmark changed (the verdict is benchx's; --all lists every row).
```

After the summary, `--tables` prints what `spin bench --compare` prints, laid out as asv lays it out: a
table of each commit (a value `8.26±0.2μs` per size, the `±` being the spread of the per-round
medians), then a table of the changes, which has only the changed rows: here there are none. `--all`
lists every row, with the noise and the verdict repeated; run by hand,
`bx compare --run numpy-revisions --baseline c5ab79c14c --tables --all` ends with

```
| Change   | Before [c5ab79c1]   | After [8bcb2e72]   |   Ratio |   Noise | Verdict            | Benchmark (Parameter)                      |
|----------|---------------------|--------------------|---------|---------|--------------------|--------------------------------------------|
|          | 8.26±0.2μs          | 8.26±0.09μs        |    1.00 |   0.97% | no change detected | bench_function_base.Mean.time_mean(1)      |
|          | 8.33±0.1μs          | 8.41±0.09μs        |    1.01 |   0.79% | no change detected | bench_function_base.Mean.time_mean(10)     |
|          | 162±2μs             | 164±2μs            |    1.01 |   0.83% | no change detected | bench_function_base.Mean.time_mean(100000) |
```

A case is a change when its effect, the mean relative difference of the paired rounds, is more than
`k` (3) times its noise. These calls take microseconds, so a run to run spread of a few percent is
normal, and a pair of revisions that differ in nothing can show a small "improvement" or
"regression" now and then. `differs: benchmark.revision.key` says that each side's benchmark is the
copy in its own revision. `out/store.parquet` holds the results (try `bx head --table`). benchx 0.1.0, from PyPI, prints the three rows without the `[size=...]`.

## Notes

- **`setup-per-call-unbatched`.** `Mean` has a `setup`, so, as in asv_runner >= 0.3.0, every timed call
  sees fresh state: one call per loop, with the setup re-run between calls outside the timer. For a
  call this short that timing includes some timer overhead, and the result is flagged.
- **Why a loop, and not one `bx compare A B`.** With a target of its own, `bx compare` runs both sides
  in one command, as the pyperf adapter does by putting each build first on `sys.path`. The asv
  adapter does not do that yet: it runs the `python` on the `PATH`, and the target only says which
  tree is recorded. So the two builds are selected by `PYTHONPATH`, one `bx bench` call at a time.
  benchx does not record `PYTHONPATH`, which is why `compare.sh` prints the numpy each call imports.
- **The suite is each revision's own.** An asv suite outside the checkout being measured does not work
  with `bx bench` yet. Each result records asv's hash of its benchmark's code in its protocol, so a
  benchmark that was edited between the two revisions starts a new series.
- **BLAS threads.** A benchmark that calls BLAS, such as `bench_linalg.Eindot.time_matmul_a_b`, uses
  all the cores by default, and is very noisy on a many-core machine: here it gave an effect of +91%
  against a noise of 117%. `OPENBLAS_NUM_THREADS=1 ./compare.sh -t bench_linalg.Eindot.time_matmul_a_b v2.4.0 v2.4.3`
  pins it: the workers inherit the variable, benchx records it, and the same pair then gave +0.10%
  against 0.56%.
- **Skipped module.** `bench_lib.py` imports `asv_runner`, which is not installed, so benchx skips
  that module, and says so on every `bx bench` call.
- **Python and the build must match.** `python` on the `PATH` runs the benchmark, so it must be the
  Python `spin` built with, here 3.12; the environment provides both.
- Tried with Python 3.12, `spin` 0.15, OpenBLAS 0.3.34 and GCC 15.3 on Linux, with benchx 0.1.0 and
  with a checkout of benchx.

## What is in this directory

| File | Role |
|---|---|
| `compare.sh` | the driver: builds, the loop, the comparison |
| `benchx.conf.json` | the project file: the timing (precision, as pyperf takes it; asv takes it too), the collector, the `revisions` profile, the paths. Nothing asv's: `compare.sh` passes `--adapter asv --suite ...` |
| `numpy_facts.py` | a context collector: how the numpy this Python imports was built (BLAS, LAPACK, compiler, SIMD). benchx matches these facts between the sides, so they agree only if both builds were configured alike. There is no numpy version among them, on purpose: it would differ. |
| `environment.yml` | an environment to build and run in |
