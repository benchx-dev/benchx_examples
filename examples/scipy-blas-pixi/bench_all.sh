#!/usr/bin/env bash
# Benchmark alternately in each environment for N_ROUNDS rounds, one slot per call.
set -euo pipefail

n_rounds=$1
for round in $(seq 0 $((n_rounds - 1))); do
  pixi run -e accelerate _bench "$round" $((2 * round))
  pixi run -e openblas _bench "$round" $((2 * round + 1))
done
