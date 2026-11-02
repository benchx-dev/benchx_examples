import numpy as np

N = 400
a = np.eye(N)
b = np.ones((N, N))

def bench_matmul():
    return np.matmul(a, b)
