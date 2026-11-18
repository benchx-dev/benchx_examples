"""Print how the numpy that this Python imports was built, as one JSON object.

benchx runs this as the collector in benchx.conf.json, once per `bx bench` call, in the
environment of the call (the `PYTHONPATH` that compare.sh sets selects the numpy it imports).

    blas, lapack   name and version of the library numpy was built against
    c_compiler     name and version of the C compiler
    simd_baseline, simd_found    the SIMD extensions numpy was built for, and detected
    summary        the same, for the results

There is no numpy version here, on purpose. benchx matches a collector's facts between
the two sides of a revisions comparison, which may differ in nothing but the revision,
so facts that name the version would make every comparison fail. Here the sides agree
only if both builds were configured alike, which is what a comparison of two revisions
wants to know.
"""

import json

import numpy

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
print(json.dumps({**facts, "summary": facts}, sort_keys=True))
