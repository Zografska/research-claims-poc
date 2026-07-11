#!/bin/bash
#SBATCH --job-name=naturasi-scrape
#SBATCH --partition=light
#SBATCH --account=evaluation
#SBATCH --qos=light
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --output=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/naturasi-%j.out
#SBATCH --error=/home/users/alireza.mahmoudian.stud/research-claims-poc/logs/naturasi-%j.err

set -euo pipefail

cd "$HOME/research-claims-poc"
source .venv/bin/activate

STAMP=$(date +%d.%m_%H)
mv "logs/naturasi-$SLURM_JOB_ID.out" "logs/naturasi-$STAMP.out"
mv "logs/naturasi-$SLURM_JOB_ID.err" "logs/naturasi-$STAMP.err"

python naturasi_main.py --concurrency 40
