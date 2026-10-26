# run a single benchmarks for a pre-built numpy, check the effect of setting OPENBLAS_NUM_THREADS
#
export NUMPY=${NUMPY:-~/repos/numpy}
export BUILD=$NUMPY/build-install   # the build directory the provider reports
rev=`git -C $NUMPY rev-parse --short main`

# hack: path to the spin-built numpy
export PYTHONPATH=$BUILD/usr/lib/python3.12/site-packages/
python -c"import numpy as np; print('\n>>>> ', np.__version__)"
echo $rev

# benchmark!
OPENBLAS_NUM_THREADS=10 bx bench @numpy --suite "$PWD/bench_linalg.py" --run-key "numpy-$rev-threads-10"
OPENBLAS_NUM_THREADS=1 bx bench @numpy --suite "$PWD/bench_linalg.py" --run-key "numpy-$rev-threads-1"
bx bench @numpy --suite "$PWD/bench_linalg.py" --run-key "numpy-$rev-threads-default"

# report
bx head --table
