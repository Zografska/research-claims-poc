#!/bin/bash
#SBATCH --job-name=sync-onedrive
#SBATCH --partition=light
#SBATCH --account=evaluation
#SBATCH --qos=light
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --output=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/sync-%j.out
#SBATCH --error=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/sync-%j.err

set -euo pipefail

cd "$HOME/research-claims-poc"
source .venv/bin/activate

SITES="${1:-coop carrefour eurospin naturasi conad}"
LOGNAME="sync-${1:-all}-$(date +%d.%m_%H)"
mv "logs/sync-$SLURM_JOB_ID.out" "logs/${LOGNAME}.out"
mv "logs/sync-$SLURM_JOB_ID.err" "logs/${LOGNAME}.err"

for SITE in $SITES; do
    ./sync_onedrive.sh "$SITE"
done
