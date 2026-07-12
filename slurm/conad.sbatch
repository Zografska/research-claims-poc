#!/bin/bash
#SBATCH --job-name=conad-scrape
#SBATCH --partition=light
#SBATCH --account=evaluation
#SBATCH --qos=light
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --output=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/conad-%j.out
#SBATCH --error=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/conad-%j.err

set -euo pipefail

cd "$HOME/research-claims-poc"
source .venv/bin/activate

STAMP=$(date +%d.%m_%H)
mv "logs/conad-$SLURM_JOB_ID.out" "logs/conad-$STAMP.out"
mv "logs/conad-$SLURM_JOB_ID.err" "logs/conad-$STAMP.err"

python conad_main.py --concurrency 1 --breaker-window-minutes 15 --breaker-pause-minutes 20

./slurm/sync_onedrive.sh conad
