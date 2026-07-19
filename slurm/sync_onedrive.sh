#!/bin/bash
set -uo pipefail

SITE="$1"

cd "$(dirname "$0")/.."

set -a
source .env 2>/dev/null || true
set +a

WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"

notify_discord() {
    local message="$1"
    local level="$2"
    [ -z "$WEBHOOK_URL" ] && return 0
    python3 -c "
import json, urllib.request, sys
colors = {'start': 0x3B82F6, 'checkpoint': 0x22D3EE, 'success': 0x22C55E, 'warning': 0xF59E0B, 'error': 0xEF4444}
payload = {'embeds': [{'description': sys.argv[1], 'color': colors.get(sys.argv[2])}]}
req = urllib.request.Request(sys.argv[3], data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
try:
    urllib.request.urlopen(req, timeout=10)
except Exception as e:
    print(f'Discord notification failed: {e}', file=sys.stderr)
" "$message" "$level" "$WEBHOOK_URL"
}

module load rclone/1.66.0 2>/dev/null || true
if ! command -v rclone >/dev/null 2>&1; then
    fallback=$(find /exa/software/Spack-2023/spack/opt/spack/linux-rocky8-icelake/gcc-13.1.0 -maxdepth 3 -type f -path '*/rclone-1.66.0-*/bin/rclone' 2>/dev/null | head -1)
    [ -n "$fallback" ] && export PATH="$(dirname "$fallback"):$PATH"
fi

notify_discord "▶️ **${SITE} — OneDrive sync started**" "start"

total_ok=0
total_fail=0
total_uploaded=0
last_checkpoint=0
CHECKPOINT_EVERY=1000

run_dirs=(raw_data/${SITE}/*/)
total_runs=${#run_dirs[@]}
run_idx=0

grand_total=0
for run_dir in "${run_dirs[@]}"; do
    [ -d "$run_dir" ] || continue
    summary="${run_dir}run_summary.json"
    if [ -f "$summary" ]; then
        status=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('status','unknown'))" "$summary" 2>/dev/null || echo "unreadable")
    else
        status="missing_summary"
    fi
    [ "$status" != "complete" ] && continue
    for img_dir in "${run_dir}"*/; do
        [ -d "$img_dir" ] || continue
        grand_total=$((grand_total + $(find "$img_dir" -type f | wc -l)))
    done
done

for run_dir in "${run_dirs[@]}"; do
    [ -d "$run_dir" ] || continue
    run_idx=$((run_idx + 1))
    ts=$(basename "$run_dir")
    summary="${run_dir}run_summary.json"
    if [ -f "$summary" ]; then
        status=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('status','unknown'))" "$summary" 2>/dev/null || echo "unreadable")
    else
        status="missing_summary"
    fi
    if [ "$status" != "complete" ]; then
        echo "Skipping raw_data/${SITE}/${ts}: status=${status}"
        continue
    fi

    img_dirs=("${run_dir}"*/)
    has_content=0
    for img_dir in "${img_dirs[@]}"; do
        [ -d "$img_dir" ] || continue
        if [ -n "$(find "$img_dir" -type f -print -quit)" ]; then
            has_content=1
            break
        fi
    done
    if [ "$has_content" -eq 0 ]; then
        echo "Skipping raw_data/${SITE}/${ts}: no category folders left, already synced"
        continue
    fi

    run_ok=1
    total_categories=${#img_dirs[@]}
    i=0
    for img_dir in "${img_dirs[@]}"; do
        [ -d "$img_dir" ] || continue
        i=$((i + 1))
        category=$(basename "$img_dir")

        cat_files=$(find "$img_dir" -type f | wc -l)
        if [ "$cat_files" -eq 0 ]; then
            echo "[$(date '+%H:%M:%S')] ${category} (${i}/${total_categories}): already empty, skipping"
            continue
        fi

        echo "[$(date '+%H:%M:%S')] ${category} (${i}/${total_categories}): syncing ${cat_files} files..."
        cat_start=$SECONDS
        if rclone move "$img_dir" "ONEDRIVE:research-claims-data/raw_data/${SITE}/${ts}/${category}" --transfers 4 --checkers 16 --tpslimit 10 --retries 5 --low-level-retries 20 --delete-empty-src-dirs --log-level INFO 2>&1 | while IFS= read -r line; do
            case "$line" in
                *ERROR*) echo "$line" >&2 ;;
                *) echo "$line" ;;
            esac
        done; then
            echo "[$(date '+%H:%M:%S')] ${category}: done in $((SECONDS - cat_start))s"
            total_uploaded=$((total_uploaded + cat_files))
        else
            run_ok=0
            echo "[$(date '+%H:%M:%S')] ${category}: FAILED after $((SECONDS - cat_start))s" >&2
        fi

        if [ $((total_uploaded / CHECKPOINT_EVERY)) -gt $((last_checkpoint / CHECKPOINT_EVERY)) ]; then
            last_checkpoint=$total_uploaded
            notify_discord "📊 **${SITE}**: ${total_uploaded}/${grand_total} images uploaded so far" "checkpoint"
        fi
    done

    for img_dir in "${img_dirs[@]}"; do
        [ -d "$img_dir" ] || continue
        if [ -z "$(find "$img_dir" -type f -print -quit)" ]; then
            rmdir "$img_dir" 2>/dev/null || true
        fi
    done

    if [ $run_ok -eq 1 ]; then
        total_ok=$((total_ok + 1))
        if [ $run_idx -lt $total_runs ]; then
            notify_discord "✅ **${SITE} — ${ts} images synced to OneDrive**" "checkpoint"
        fi
    else
        total_fail=$((total_fail + 1))
        notify_discord "⚠️ **${SITE} — ${ts} some image folders failed to sync**"$'\n'"Check \`logs/sync-${SITE}-*.out\`" "warning"
    fi
done

if [ $total_fail -eq 0 ]; then
    notify_discord "✅ **${SITE} — OneDrive sync complete**"$'\n'"${total_ok} run(s) synced, 0 failures" "success"
else
    notify_discord "⚠️ **${SITE} — OneDrive sync finished with failures**"$'\n'"${total_ok} succeeded, ${total_fail} failed" "warning"
    exit 1
fi
