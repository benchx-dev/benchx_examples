"""Example of DIY reading the stored results.

Median numpy matmul time vs matrix size, for one run in the benchx store.
Usage:
    python numpy_vs_size.py out/home/store.parquet RUN_KEY
"""
import json
import statistics
import sys
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt

import pyarrow.parquet as pq


# usage: print_sizes.py path/to/store.parquet run-key
store, run_key = sys.argv[1], sys.argv[2]

times_numpy = defaultdict(list)
times_torch = defaultdict(list)

for text in pq.read_table(store, columns=["document"]).column("document").to_pylist():
    doc = json.loads(text)
    if doc["provenance"]["run_key"] != run_key:
        continue
    workload, measurement = doc["coordinates"]["workload"], doc["measurement"]
    if workload["name"] != "bench_matmul" or measurement["quantity"]["name"] != "wall-time":
        continue
    params = workload["parameters"]  # values as their repr: {"n": "10", "xp": "'numpy'"}

    if params["xp"] == "'numpy'":
        times_numpy[int(params["n"])] += [o["value"] for o in measurement.get("observations", [])]
    if params["xp"] == "'torch'":
        times_torch[int(params["n"])] += [o["value"] for o in measurement.get("observations", [])]


medians_numpy, medians_torch, ns = [], [], []

for n in sorted(times_numpy):
    ns.append(int(n))
    medians_torch.append(statistics.median(times_numpy[n]) * 1e6)  # in us
    medians_numpy.append(statistics.median(times_torch[n]) * 1e6)


print(f"\n>>> numpy: ")
for n, time in zip(ns, medians_numpy):
    print(f"{int(n):5d}  {time:8.2f} us")

print(f"\n>>> torch: ")
for n, time in zip(ns, medians_torch):
    print(f"{int(n):5d}  {time:8.2f} us")

plt.loglog(ns, medians_numpy, 'o--', label="numpy")
plt.loglog(ns, medians_torch, 'o--', label="torch")

plt.grid(True)
plt.legend(loc='best')
plt.savefig('times.png')

