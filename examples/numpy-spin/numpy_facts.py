"""Print what the numpy that this Python imports says about itself, as one JSON object.

Both the provider (provider.py, which declares these facts as the target's how_built)
and the collector (collectors in benchx.conf.json, which observes them in the workers'
environment) run this script, so the two can only differ if the environment does.

    numpy_version  numpy.__version__
    show_config    numpy.show_config(mode="dicts"): compiler, BLAS/LAPACK, SIMD, ...
    imported_from_target   whether that numpy lives under the directory this runs in,
                   the target's ($BUILD). An observation, not a fact about the build
    summary        a few readable facts; collectors put these in each result

`imported_from_target` is false when PYTHONPATH does not lead into the build, and the
numpy found is another one, such as an installed numpy of the same version, which the
version check cannot tell from the build. The provider and the collector's `expect` in
benchx.conf.json refuse the run then.
"""

import json
import sys
from pathlib import Path

import numpy

config = numpy.show_config(mode="dicts")
dependencies = config.get("Build Dependencies", {})
compilers = config.get("Compilers", {})
simd = config.get("SIMD Extensions", {})


def named(entry):
    return {key: entry.get(key) for key in ("name", "version")}


target = Path.cwd().resolve()
imported_from_target = Path(numpy.__file__).resolve().is_relative_to(target)
if not imported_from_target:
    print(f"numpy was imported from {numpy.__file__}, which is not under {target}", file=sys.stderr)

print(json.dumps({
    "numpy_version": numpy.__version__,
    "show_config": config,
    "imported_from_target": imported_from_target,
    "summary": {
        "numpy_version": numpy.__version__,
        "blas": named(dependencies.get("blas", {})),
        "lapack": named(dependencies.get("lapack", {})),
        "c_compiler": named(compilers.get("c", {})),
        "simd_baseline": simd.get("baseline"),
        "simd_found": simd.get("found"),
        "imported_from_target": imported_from_target,
    },
}, sort_keys=True))
