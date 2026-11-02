"""Print how the numpy that this Python imports was built, as one JSON object.

Both the provider (provider.py, which declares these facts as the target's how_built)
and the collector (collectors in benchx.conf.json, which observes them in the workers'
environment) run this script, so the two can only differ if the environment does.

    blas, lapack   name and version of the library numpy was built against
    c_compiler     name and version of the C compiler
    simd_baseline, simd_found    the SIMD extensions numpy was built for, and detected
    imported_from_target    whether the numpy imported here lives under the directory
                   this runs in, the target's. An observation, not a fact about the build
    summary        the same, for the results

There is no numpy version here, on purpose. benchx matches a collector's facts between
the two sides of a revisions comparison, which may differ in nothing but the revision,
so facts that name the version would make every comparison fail. Here the sides agree
only if both builds were configured alike, which is what a comparison of two revisions
wants to know.

`imported_from_target` checks which build is imported without naming it. It is true on
both sides, so `sides-agree` has nothing to object to, but it is computed against each
side's own target directory: it is false when the numpy that gets imported is not in the
side's own build, such as another numpy that PYTHONPATH or the environment provides when
the target is not the directory that holds the package. The collector's `expect` in
benchx.conf.json then refuses the run. This emulates the benchmark's import (it puts the
target first on sys.path, as pyperf does for the benchmark, after the suite's own
directory); the benchmark's own process is not observed.
"""

import json
import sys
from pathlib import Path

# The directory this runs in holds the package (benchx runs collectors in the target's
# directory, as pyperf puts it first on sys.path for the benchmark), so import from there.
target = Path.cwd().resolve()
sys.path.insert(0, str(target))

import numpy  # noqa: E402

config = numpy.show_config(mode="dicts")
dependencies = config.get("Build Dependencies", {})
compilers = config.get("Compilers", {})
simd = config.get("SIMD Extensions", {})


def named(entry):
    return {key: entry.get(key) for key in ("name", "version")}


facts = {
    "blas": named(dependencies.get("blas", {})),
    "lapack": named(dependencies.get("lapack", {})),
    "c_compiler": named(compilers.get("c", {})),
    "simd_baseline": simd.get("baseline"),
    "simd_found": simd.get("found"),
}
imported_from_target = Path(numpy.__file__).resolve().is_relative_to(target)
if not imported_from_target:
    print(f"numpy was imported from {numpy.__file__}, which is not under {target}", file=sys.stderr)
print(json.dumps({**facts, "imported_from_target": imported_from_target,
                  "summary": {**facts, "imported_from_target": imported_from_target}}, sort_keys=True))
