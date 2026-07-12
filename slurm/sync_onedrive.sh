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

notify_discord "▶️ **${SITE} — OneDrive sync started**" "start"

total_ok=0
total_fail=0

run_dirs=(raw_data/${SITE}/*/)
total_runs=${#run_dirs[@]}
run_idx=0

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
    run_ok=1
    img_dirs=("${run_dir}"*/)
    total_categories=${#img_dirs[@]}
    checkpoint_interval=$(( total_categories / 5 > 0 ? total_categories / 5 : 1 ))
    i=0
    for img_dir in "${img_dirs[@]}"; do
        [ -d "$img_dir" ] || continue
        i=$((i + 1))
        category=$(basename "$img_dir")
        log="logs/rclone-sync-${SITE}-${ts}-${category}.log"
        if ! rclone move "$img_dir" "ONEDRIVE:research-claims-data/raw_data/${SITE}/${ts}/${category}" --transfers 4 --checkers 16 --tpslimit 10 --retries 5 --low-level-retries 20 --delete-empty-src-dirs --log-file="$log" --log-level INFO; then
            run_ok=0
        fi
        if [ $((i % checkpoint_interval)) -eq 0 ]; then
            notify_discord "📊 **${SITE} — ${ts}**: ${i}/${total_categories} categories synced" "checkpoint"
        fi
    done

    if [ $run_ok -eq 1 ]; then
        total_ok=$((total_ok + 1))
        if [ $run_idx -lt $total_runs ]; then
            notify_discord "✅ **${SITE} — ${ts} images synced to OneDrive**" "checkpoint"
        fi
    else
        total_fail=$((total_fail + 1))
        notify_discord "⚠️ **${SITE} — ${ts} some image folders failed to sync**"$'\n'"Check \`logs/rclone-sync-${SITE}-${ts}-*.log\`" "warning"
    fi
done

if [ $total_fail -eq 0 ]; then
    notify_discord "✅ **${SITE} — OneDrive sync complete**"$'\n'"${total_ok} run(s) synced, 0 failures" "success"
else
    notify_discord "⚠️ **${SITE} — OneDrive sync finished with failures**"$'\n'"${total_ok} succeeded, ${total_fail} failed" "warning"
    exit 1
fi
