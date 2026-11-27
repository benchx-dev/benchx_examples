# scipy-blas-pixi: using benchx with Pixi to benchmark different BLAS implementations on conda-forge with SciPy

- Benchmarks `scipy.linalg.cholesky` (500×500) with `scipy 1.18.1` in two osx-arm64 Pixi environments.
- The environments differ only in the BLAS implementation: Accelerate vs. OpenBLAS.
  - Note: BLAS thread counts are not pinned, they use the default.
- Run: `pixi run compare`.

- `describe_env.py` records SciPy version, blas version, and blas build.

- TODO: make this kind of comparison nicely explorable in `bx view`
