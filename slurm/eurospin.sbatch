#!/bin/bash
#SBATCH --job-name=eurospin-scrape
#SBATCH --partition=light
#SBATCH --account=evaluation
#SBATCH --qos=light
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --output=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/eurospin-%j.out
#SBATCH --error=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/eurospin-%j.err

set -euo pipefail

cd "$HOME/research-claims-poc"
source .venv/bin/activate

STAMP=$(date +%d.%m_%H)
mv "logs/eurospin-$SLURM_JOB_ID.out" "logs/eurospin-$STAMP.out"
mv "logs/eurospin-$SLURM_JOB_ID.err" "logs/eurospin-$STAMP.err"

python eurospin_main.py --concurrency 40

./slurm/sync_onedrive.sh eurospin
