"""
One scipy call that goes straight to LAPACK/BLAS:
the Cholesky factorization of a 500x500 symmetric positive definite matrix.
"""

import numpy as np
import scipy.linalg

_rng = np.random.default_rng(0)
_a = _rng.standard_normal((500, 500))
_spd = _a @ _a.T + 500 * np.eye(500)


def bench_cholesky():
    scipy.linalg.cholesky(_spd)
