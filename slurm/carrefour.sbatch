#!/bin/bash
#SBATCH --job-name=carrefour-scrape
#SBATCH --partition=light
#SBATCH --account=evaluation
#SBATCH --qos=light
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --output=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/carrefour-%j.out
#SBATCH --error=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/carrefour-%j.err

set -euo pipefail

cd "$HOME/research-claims-poc"
source .venv/bin/activate

STAMP=$(date +%d.%m_%H)
mv "logs/carrefour-$SLURM_JOB_ID.out" "logs/carrefour-$STAMP.out"
mv "logs/carrefour-$SLURM_JOB_ID.err" "logs/carrefour-$STAMP.err"

python carrefour_main.py --concurrency 15 --breaker-rate-limited-threshold 10 --breaker-window-minutes 10 --breaker-pause-minutes 10

./sync_onedrive.sh carrefour
