#!/bin/zsh
RID=20261024-154813-a62448
for i in {1..40}; do
  sleep 15
  R=$(curl -s -m 10 "http://127.0.0.1:8001/api/research/status")
  if [[ "$R" != *"$RID"* ]]; then
    echo "finished after $((i*15))s"
    break
  fi
  echo "  still running ($((i*15))s)"
done
echo '--- after ---'
python3 -c "
import json
d = json.load(open('/Users/shitaosun/Project/AI-Personal/SignalForge/data/research/runs/$RID/report.json'))
m = d['metrics']
print('claims_by_verdict:', m['claims_by_verdict'])
print('claims_total:', m['claims_total'])
print('sections_passed:', m['sections_passed'], '/', m['sections_total'])
print('validator_problems:', m['validator_problems'])
"
