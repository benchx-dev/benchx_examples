# run a single benchmarks for several numpy revisions, in a fixed environment, with `spin build`
#
export NUMPY=${NUMPY:-~/repos/numpy}
export BUILD=$NUMPY/build-install   # the build directory the provider reports
MAIN=`git -C $NUMPY rev-parse --short main`
failed=()

# NB: v2.30 is deliberately wrong, to probe build failure mode (build failure is not a result)

for rev in $MAIN v2.4.3 v2.4.0 v2.30; do
    echo "=== $rev"

    # change to the numpy source and build numpy
    pushd $NUMPY
    if ! git -c advice.detachedHead=false checkout $rev; then
        popd; failed+=($rev); continue
    fi
    git submodule update --init
    echo `git rev-parse --short HEAD`

    spin build
    if [ $? -ne 0 ]; then
        echo "!!! $rev: build failed" >&2
        popd; failed+=($rev); continue
    fi
    popd

    # hack: path to the spin-built numpy
    export PYTHONPATH=$BUILD/usr/lib/python3.12/site-packages/
    python -c"import numpy as np; print('\n>>>> ', np.__version__)"
    echo $rev

    # benchmark!
    bx bench @numpy --suite "$PWD/bench_linalg.py" --run-key "numpy-$rev" || failed+=($rev)
done

if [ ${#failed[@]} -gt 0 ]; then
    echo "failed revisions: ${failed[*]}" >&2
fi


# XXX: suite paths: absolute or relative to root, not benchmark root
# XXX: a case that crashes or times out is still a stored `error` result and bx bench exits 0

# report
bx head --table
