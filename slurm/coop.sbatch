#!/bin/bash
#SBATCH --job-name=coop-scrape
#SBATCH --partition=light
#SBATCH --account=evaluation
#SBATCH --qos=light
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --output=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/coop-%j.out
#SBATCH --error=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/coop-%j.err

set -euo pipefail

cd "$HOME/research-claims-poc"
source .venv/bin/activate

STAMP=$(date +%d.%m_%H)
mv "logs/coop-$SLURM_JOB_ID.out" "logs/coop-$STAMP.out"
mv "logs/coop-$SLURM_JOB_ID.err" "logs/coop-$STAMP.err"

python coop_main.py --concurrency 40
