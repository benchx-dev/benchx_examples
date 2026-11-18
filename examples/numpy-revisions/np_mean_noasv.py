"""
# https://github.com/numpy/numpy/blob/main/benchmarks/benchmarks/bench_function_base.py#L62-L73

class Mean(Benchmark):
    param_names = ['size']
    params = [[1, 10, 100_000]]

    def setup(self, size):
        self.array = np.arange(2 * size).reshape(2, size)

    def time_mean(self, size):
        np.mean(self.array)

    def time_mean_axis(self, size):
        np.mean(self.array, axis=1)
"""


import numpy as np


def setup_array(size):
    return np.arange(2 * size).reshape(2, size)


SIZES = [1, 10, 100_000]
ARRAYS = {size: setup_array(size) for size in SIZES}


def bench_mean(size):
    arr = ARRAYS[size]
    return np.mean(arr)
bench_mean.params = [[1, 10, 100_000]]
bench_mean.param_names = ['size']


def bench_mean_axis(size):
    arr = ARRAYS[size]
    return np.mean(arr, axis=-1)
bench_mean_axis.params = [[1, 10, 100_000]]
bench_mean_axis.param_names = ['size']

