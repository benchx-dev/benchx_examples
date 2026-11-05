# pandas-asv: one pandas asv benchmark, two pandas versions

One benchmark from pandas' own [asv](https://asv.readthedocs.io) suite, run unchanged by
`bx bench PATH --adapter asv` under two pandas versions, each in its own virtual environment,
alternated round by round, then compared. The asv adapter reads asv's benchmark format as a
language (discovery, `params`, `setup`, `setup_cache`, asv's benchmark version hash) and times it
with pyperf: neither asv nor asv_runner is installed.

The suite is pandas' `asv_bench/` at one tag (`v3.1.1`), the same for both sides; only the
installed pandas differs. That is
[UC-04](https://github.com/benchx-dev/benchx/blob/main/docs/use-cases/UC-04-cross-env.md),
"fixed branch, comparing environments", driven the same way as `examples/numpy-venvs`.

The case is `strings.Methods.time_lower('str')`: one parameter combination of one benchmark.
`dtype="str"` is object dtype in pandas 2.x and the pyarrow-backed string dtype from pandas 3.0,
so the two sides are expected to differ.

## Run it

You need [`uv`](https://docs.astral.sh/uv/), git, and network access the first time. You also
need benchx, installed in editable mode from a checkout, in the active environment. Then, from
this directory:

```console
$ git clone https://github.com/benchx-dev/benchx.git
$ python3 -m venv .venv && . .venv/bin/activate    # Python >= 3.11, or any environment you like
$ pip install -e benchx/prototype
$ ./run.sh
```

The script installs that same checkout in both venvs. It finds it from the benchx in the active
environment; `BENCHX_SRC=<checkout>/prototype ./run.sh` names it instead.

The tag, the two pandas versions, the case, the Python and the number of rounds are set at the
top of `run.sh`. Everything it creates is in `pandas/`, `.venv-a`, `.venv-b` and `out/`, all
git-ignored. A run takes under a minute after the venvs are cached.

## What it does

1. **Fetches the suite.** A shallow, sparse clone of pandas at `v3.1.1`, with only `asv_bench/`
   checked out (a few MB). Nothing is built: the benchmarks import the pandas installed in each
   venv, and each case runs from a scratch directory, so the unbuilt checkout cannot shadow it.
2. **Prepares two venvs**, `.venv-a` with pandas 2.3.3 and `.venv-b` with pandas 3.1.1, each
   with pyarrow, pyperf and benchx.
3. **Runs the caller's loop.** For each of the 3 rounds, one call per side, in its venv:

   ```console
   $ bx bench pandas/asv_bench --adapter asv "strings.Methods.time_lower('str')" \
       --run-key "$RUN_KEY" --label env=pandas-2.3.3 --round 0 --slot 0 --out "out/$RUN_KEY"
   ```

   `pandas/asv_bench` holds `asv.conf.json`, whose `benchmark_dir` is the suite; its checkout
   is the target. The exact case name selects one parameter combination; `--filter REGEX`
   (asv's `--bench`) would select by pattern instead. Modules the venv cannot import (no
   matplotlib, scipy, ...) are listed on stderr and skipped. Each call prints a table:

   ```
   case                                      median    mean ± sd            min .. max            n   status
   ----------------------------------------  --------  -------------------  --------------------  --  -----------------------------------
   strings.Methods.time_lower [dtype='str']  890.2 us  937.6 us ± 122.9 us  835.2 us .. 1.202 ms  10  success  [setup-per-call-unbatched]
   ```

4. **Compares.** `bx compare --run S --profile environments --label env --baseline pandas-2.3.3`:

   ```
   run pandas-1793878687  profile environments  baseline pandas-2.3.3  contender pandas-3.1.1
     differs: coordinates.environment.system.deps.pandas, coordinates.environment.system.deps.sha256
     caveats: baseline: setup-per-call-unbatched, contender: setup-per-call-unbatched

   IMPROVED (1)
     strings.Methods.time_lower       wall-time  effect  -85.40%  noise   1.76%  rounds=3
   ```

   (The numbers vary from run to run.)
5. **Lists the series.** One per environment, because the collected pandas version is part of
   a series' identity. Every point carries the suite's revision (pandas `v3.1.1`), whichever
   pandas it ran under: the target is the checkout the benchmarks come from, and what varies is
   the environment, recorded by the collector.

## How it is configured

`benchx.conf.json` is found by walking up from the working directory, so `bx` reads it when
`run.sh` runs from here:

- `adapter`: the harness (`asv`) and its precision, in pyperf's terms: 2 processes (asv's
  rounds) × 5 values (asv's repeat), 1 warmup, loops calibrated. Flags such as `--processes`,
  `--values`, `--min-time` and `--loops` override them per call. What neither gives comes from
  each benchmark's own `repeat`, `number`, `sample_time` and `warmup_time`.
- `collectors.deps`: `describe_env.py`, a **context collector**. benchx runs it once per call,
  in the environment the call runs in, and it prints the pandas, numpy and pyarrow it imports.
  That lands in each result's `environment.system.deps`, which is how the `environments`
  comparison knows what differs between the sides.
- `paths`: the store and the results go in `out/`.

Each result also records the installed project's version (`provenance.info.asv.installed`) and
asv's hash of the benchmark's code (`protocol.asv.benchmark_version`), so editing the benchmark
starts a new series.

## Caveats

- **`setup-per-call-unbatched`.** `Methods` has a `setup`, so, as in asv_runner >= 0.3.0, every
  timed call sees fresh state: one call per loop, setup re-run between calls outside the timer.
  For a ~100 µs call that timing includes some timer overhead, and the result is flagged. A
  benchmark whose calls leave the set-up state intact can declare `setup_scope = "sample"`.
- **Memory benchmarks** (`peakmem_*`, `mem_*`) and other non-`time_*` types are listed and
  skipped.
- **Unstable boot time.** pyperf's `boot_time` metadata is part of `environment.system`, which
  the `environments` profile uses to tell sides apart. On hosts where the kernel's boot time
  drifts (seen on WSL2), calls with the same label can then become separate sides, and the
  comparison fails the `two-sides` invariant. This is a benchx issue, not specific to asv.

## What is in this directory

| File | Role |
|---|---|
| `run.sh` | the driver: the suite, the venvs, the loop, the comparison |
| `benchx.conf.json` | the project file: the adapter and its precision, the `deps` collector, the paths |
| `describe_env.py` | the collector: prints the pandas, numpy and pyarrow this Python imports |
