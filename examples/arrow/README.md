# Arrow-shaped examples: Google Benchmark and CMake

Two end-to-end examples in the shape of the Arrow local-benchmarking story, on one
small stand-in suite. They used to live in the benchx repository, as
`prototype/examples/{demo-suite,demo,archery-local}` and `prototype/demo.sh`.

| Directory | What it is |
|---|---|
| `demo-suite/` | a two-benchmark Google Benchmark suite (`BM_Quiet` and `BM_Noisy`), built with CMake; `-DDEMO_HARDENED=ON` adds about 3% of work |
| `demo/` | `run.sh`, a walkthrough of both comparison profiles that prints every command before running it; the project file (`benchx.conf.json`) and the local store it keeps |
| `archery-local/` | a target provider walkthrough: one commit built plain and hardened, and compared; has its own README |

## Run them

You need benchx installed in editable mode from a checkout (it reads its schemas from
there), `cmake`, a C++ compiler, `git` and `python3`, and network access the first time
(CMake fetches Google Benchmark unless it is installed). From the root of this
repository:

```console
$ git clone https://github.com/benchx-dev/benchx.git
$ python3 -m venv .venv && . .venv/bin/activate    # Python >= 3.11
$ pip install -e benchx/prototype
$ bash examples/arrow/demo/run.sh
$ bash examples/arrow/archery-local/run.sh
```

`ROUNDS=2` shortens either one; the default is 5.

## What `demo/run.sh` shows

It prepares a git source with two commits and three CMake build directories of
`demo-suite` (base, head, and head with `DEMO_HARDENED=ON`), shows the first work
order of each part, then:

1. **revisions, ad hoc:** `bx compare` in measure mode alternates base and head over the
   rounds with orders that name no project, then read mode compares the same run key
   through a throwaway store;
2. **environments, tracked:** `bx compare` alternates plain and hardened, labeled
   `build: plain|hardened`, compares from the local store, re-ingests (a no-op), and
   rejects a unit conflict;
3. checks that the throwaway store gives the same comparison document as the persistent
   one, lists series and history, and ends with `bx head`.

Every measure-mode `bx compare` delivers to the local store, `demo/store.parquet`, so
each run adds its results to it. Run keys carry a timestamp, so runs accumulate and each
series' history grows. Look at it at any time, or start over:

```console
$ (cd examples/arrow/demo && python -m benchx.cli head -n 20)
$ rm examples/arrow/demo/store.parquet
```
