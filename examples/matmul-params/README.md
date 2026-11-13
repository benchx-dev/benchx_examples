# Example: one benchmark, several parameter combinations

`bench_matmul.py` times `a @ b` for square float64 arrays, for N = 10, 50, 100 and
for numpy and torch: one function, six cases. `bx bench` runs each combination as its own
case, under [pyperf](https://pyperf.readthedocs.io).

## Run it

In a virtual environment. The workers run the first `python` on the `PATH`, so the
environment must be active, and must import pyperf, numpy and torch:

```sh
python -m venv .venv && . .venv/bin/activate
pip install pyperf numpy
pip install torch --index-url https://download.pytorch.org/whl/cpu    # the CPU build
cd examples/matmul-params
export BENCHX_HOME=$PWD/out/home      # optional: keep the result store here, not in ~
bx bench bench_matmul.py --out out --run-key mm_
```

This uses pyperf's defaults (20 worker processes x 3 values, 0.1 s calibration) and takes
several minutes, mostly importing torch in every worker.

The `--run-key` argument is optional: if you do not supply it, `benchx` will generate a default
key. Specifying your own key is only useful if you want to process the stored result yourself
later (see below for an example).

## A quick version

```sh
bx bench bench_matmul.py --processes 2 --values 2 --min-time 0.01 --out out --run-key mm
```

About 15 seconds. The timings are rougher: each case has 4 values.

## Output

One row per combination, named by the function and its arguments:

```
case                              median    mean ± sd            ...
bench_matmul [n=10, xp='numpy']   1.627 us  ...
bench_matmul [n=10, xp='torch']   2.387 us  ...
...
bench_matmul [n=100, xp='torch']  23.88 us  ...
```

The result files are in `out/`, and `out/home/store.parquet` is the store. `bx` reports
twice as many results as rows: each case also records `load-average`.

## Choosing cases

```sh
bx bench bench_matmul.py bench_matmul                    # a function's name: all six
bx bench bench_matmul.py "bench_matmul(100, 'torch')"    # one combination
bx bench bench_matmul.py --filter "'torch'"              # a regex: the three torch cases
```

A regex is searched in `bench_matmul(10, 'torch')`, the function's name and the argument
values (not their names). `--filter 'bench_matmul$'` is therefore refused, since `$` leaves
no room for the arguments; the refusal says so.


## Processing the results

Benchmark results are stored as a parquet file according to the results schema, so that you
can extract and analyze them later. As an example, here is a simple script to extract and
plot the times for both numpy and pytorch versus the matrix size:

```sh
python print_sizes.py out/home/store.parquet mm_ 
```

Here the helper script, `print_sizes.py` takes two cmdline arguments: the path to the
results store and the run key, extract the benchmarked times, and saves a plot, `times.png`.


## Comparing numpy and torch

The two libraries are the two values of `xp`, so `bench_matmul` is also a
[UC-02](https://github.com/benchx-dev/benchx/blob/main/docs/use-cases/UC-02-variants.md) benchmark: the same function, run once with each
library, with the rounds interleaved. `n` is the other parameter, so each size is its own comparison and
`--vary xp` says which parameter is the one that differs.

**With a loop of `bx bench` calls.** Each call runs one library, with `--filter`, as one side of a session;
`--round` and `--slot` place it, and `bx compare --run` compares the sides:

```sh
for r in 0 1 2 3 4; do
  bx bench bench_matmul.py --filter "'numpy'" --run-key mm --round $r --slot $((2*r))   --out out
  bx bench bench_matmul.py --filter "'torch'" --run-key mm --round $r --slot $((2*r+1)) --out out
done
bx compare --run mm --profile variants --vary xp --baseline "'numpy'"
```

The result is one unit per size, with numpy as the baseline and torch as the contender: the effect is
torch's median time relative to numpy's, so `REGRESSED` means torch took longer, and the noise is taken
across the five rounds. The units are grouped by verdict. This is the output of the loop above with the
quick settings (`--processes 2 --values 2 --min-time 0.01`, added to both calls):

```
run mm  profile variants  baseline 'numpy'  contender 'torch'

REGRESSED (2)
  bench_matmul [n=10]              wall-time  effect  +17.19%  noise   0.50%  rounds=5
  bench_matmul [n=50]              wall-time  effect  +87.08%  noise  14.30%  rounds=5

IMPROVED (1)
  bench_matmul [n=100]             wall-time  effect  -53.59%  noise   1.24%  rounds=5
```

Here torch is slower than numpy at N=10 and N=50 and takes about half the time at N=100. The N=50 noise is high
with the quick settings, which take only a few values per case. `--baseline` is spelled as the
value is recorded, quotes included.

One `bx bench bench_matmul.py` call is not enough. It measures all six cases in one order, with no round and no
slot: a grid of timings, not an alternation, so `bx compare --profile variants` refuses it
(`alternating-slots`: "a result has no slot…") and the message names the two ways to get an alternating run,
the loop above and the one-command form below.

**In one command.** Measure mode runs the same loop, listing the cases once and writing one order per library
and round:

```sh
bx compare . --profile variants --adapter pyperf --suite bench_matmul.py --vary xp --rounds 5
```

It prints the same table, with the numbers of its own run (with the quick settings: +17.9%, +76.8% and
-52.7% for N=10, 50 and 100). Add the quick version's `--processes 2 --values 2 --min-time 0.01` to either form
for a rougher, faster comparison; the loop above takes about a minute and a half with them, mostly importing
torch in every worker.

## How the parameters are declared

```python
bench_matmul.params = [[10, 50, 100], ["numpy", "torch"]]   # one list per argument
bench_matmul.param_names = ["n", "xp"]
```

Combinations are the product of the lists, in this order, and the function is called with
one of them. A value is recorded as its `repr`, so the library is given by its name and
imported on first use, not passed as a module.

## What is timed

The whole body of `bench_matmul` is timed: the call to `operands(n, xp)` as well as `a @ b`.
`operands` is cached, so the arrays are made once per worker process, on its first call (a
calibration or warmup call), not in every call. What every call still pays is the cache
lookup, about 60 ns here: roughly 4% of the numpy time at N=10 and under 0.2% at N=100.
The timings include it, for numpy and torch alike. The result array of `a @ b` is also
allocated inside the timed call. In a comparison of the two libraries the lookup is a fixed cost
on both sides: it cancels in the difference but not in the percentage, so at N=10 the
percentage reads about 4% smaller than it is.
