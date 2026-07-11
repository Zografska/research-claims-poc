#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

for site in coop carrefour eurospin naturasi conad; do
    sbatch "slurm/${site}.sbatch"
done
