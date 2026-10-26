# Demo BenchX user project

Demo running an out-of-tree benchmark for NumPy. Demonstrates:
- running a benchmark for a series of commits (`track.sh`)
- NumPy is built with `spin`
- benchmarking harness is `pyperf`
- benchmark project configuration (`benchx.conf.json`)
- "target provider" stores build information
- "environment collector" collects runtime info and check consistency
  ("am I benchmarking the version I think I am benchmarking" kind of question).
- storing the results according to the schema.


Note that here we use `spin` to build numpy, and run benchmarks separately. If you control
the `spin` in your repository to be benchmarked, you may want to hide the `bx` benchmarking
invocations in a dedicated spin command instead (a la numpy's `spin bench`). This might be
simpler than what is done here, actually. The demonstration here is mainly to show what
you _can_ do only.


After running

```
$ ./track.sh
```

the bare results are in the `results/` directory, and `store.parquet` holds the ingested results. To view them, run


```
$ bx head --table
/home/ev-br/proj/quansight/benchx_user/numpy-bench/store.parquet: 3 result(s); latest 3, newest first
revision    run               project  case          median    mean ± sd            min .. max            n   status
----------  ----------------  -------  ------------  --------  -------------------  --------------------  --  -------
c5ab79c14c  numpy-v2.4.0      numpy    bench_matmul  4.127 ms  4.565 ms ± 1.639 ms  2.97 ms .. 9.843 ms   60  success
8bcb2e72e6  numpy-v2.4.3      numpy    bench_matmul  4.269 ms  4.865 ms ± 2.031 ms  2.969 ms .. 10.72 ms  60  success
6f721564ad  numpy-6f721564ad  numpy    bench_matmul  5.983 ms  5.806 ms ± 1.958 ms  2.969 ms .. 9.75 ms   60  success
```
