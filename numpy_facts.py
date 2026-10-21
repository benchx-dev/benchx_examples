"""Print what the numpy that this Python imports says about itself, as one JSON object.

Both the provider (provider.py, which declares these facts as the target's how_built)
and the collector (collectors in benchx.conf.json, which observes them in the workers'
environment) run this script, so the two can only differ if the environment does.

    numpy_version  numpy.__version__
    show_config    numpy.show_config(mode="dicts"): compiler, BLAS/LAPACK, SIMD, ...
    summary        a few readable facts; collectors put these in each result
"""

import json

import numpy

config = numpy.show_config(mode="dicts")
dependencies = config.get("Build Dependencies", {})
compilers = config.get("Compilers", {})
simd = config.get("SIMD Extensions", {})


def named(entry):
    return {key: entry.get(key) for key in ("name", "version")}


print(json.dumps({
    "numpy_version": numpy.__version__,
    "show_config": config,
    "summary": {
        "numpy_version": numpy.__version__,
        "blas": named(dependencies.get("blas", {})),
        "lapack": named(dependencies.get("lapack", {})),
        "c_compiler": named(compilers.get("c", {})),
        "simd_baseline": simd.get("baseline"),
        "simd_found": simd.get("found"),
    },
}, sort_keys=True))
