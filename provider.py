#!/usr/bin/env python3
"""Target provider for numpy: describes a spin-built numpy, builds nothing.

benchx runs this with a JSON request on stdin and reads one target description from
stdout (progress and errors go to stderr). The target is the build directory $BUILD,
where the benchmark runs; the revision is read from the checkout $NUMPY.

how_built is an object: what numpy says about itself, asked of the Python that PATH and
PYTHONPATH select, in $BUILD (numpy_facts.py). The collector in benchx.conf.json asks
the same of the benchmark's environment, and the run is refused if the two differ.

The provider also refuses to describe a numpy that is not the checkout's HEAD (a build
not redone after `git checkout`): the version of a numpy built from git ends in the
commit's hash, and a release build is the checkout's tag.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
for name in ("NUMPY", "BUILD"):
    if name not in os.environ:
        sys.exit(f"provider.py: set {name} (the numpy checkout, and its build directory)")
numpy_dir, build_dir = os.environ["NUMPY"], os.environ["BUILD"]
sys.stdin.read()  # the request is not needed

done = subprocess.run([sys.executable, str(here / "numpy_facts.py")], cwd=build_dir,
                      capture_output=True, text=True)  # not $NUMPY: its source tree would shadow the build
if done.returncode:
    sys.exit(f"provider.py: numpy in {build_dir} did not report its facts:\n{done.stderr.strip()}")
facts = json.loads(done.stdout)
facts.pop("summary")  # readable extras for the results, not part of the declaration


def git(*args):
    return subprocess.run(["git", "-C", numpy_dir, *args], capture_output=True, text=True).stdout.strip()


head, version = git("rev-parse", "HEAD"), facts["numpy_version"]
built_from = re.search(r"git\d+\.([0-9a-f]+)", version)
if not (built_from and head.startswith(built_from[1])) and git("describe", "--tags", "--exact-match") != f"v{version}":
    sys.exit(f"provider.py: numpy {version} in {build_dir} is not the checkout's HEAD {head[:10]}: rebuild")

print(json.dumps({
    "schema_version": "benchx/target-description/0.1.0",
    "target": {"kind": "build", "path": build_dir,
               "source": {"uri": "https://github.com/numpy/numpy.git", "type": "git"},
               "source_dir": numpy_dir},
    "how_built": facts,
    "provider": {"name": "provider.py", "version": "2"},
}, indent=1))
