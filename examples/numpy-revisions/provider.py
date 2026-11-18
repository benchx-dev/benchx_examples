#!/usr/bin/env python3
"""Target provider: the numpy built in $BUILD, from the checkout $NUMPY.

`bx bench @numpy` runs this and reads a target description from its stdout. The target is the build
directory, where the benchmark runs; the checkout gives the revision. Running in the build directory,
not in the checkout, keeps NumPy's unbuilt source tree off the path, as `spin bench` does by running
asv in `benchmarks/`.
"""

import json
import os
import sys

sys.stdin.read()  # the request, which is not needed

target = {
    "kind": "build",
    "path": os.environ["BUILD"],
    "source": {"uri": "https://github.com/numpy/numpy.git", "type": "git"},
    "source_dir": os.environ["NUMPY"],
}
print(json.dumps({"schema_version": "benchx/target-description/0.1.0", "target": target}, indent=1))
