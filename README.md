# Demos and worked examples of using BenchX

This repository holds a collection of worked examples of using BenchX.
These are mostly demonstration of BenchX capabilities, and may or may not
represent best practices.

Currently, the following examples are provided:

- `examples/numpy-spin`: out-of-tree benchmarks for NumPy, using `spin` to build NumPy itself;
- `examples/arrow`: Arrow-shaped examples with Google Benchmark and CMake: a walkthrough of both
  comparison profiles (`demo`) and one of the target provider contract (`archery-local`).
- `examples/pyperf-suite`: a suite of Python functions benchmarked with `bx bench`, results stored locally.
- `examples/matmul-params`: parametrized benchmarks to compare installed NumPy and PyTorch
