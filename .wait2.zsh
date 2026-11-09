#!/bin/zsh
RID=20261024-154813-a62448
for i in {1..40}; do
  sleep 15
  R=$(curl -s -m 10 http://127.0.0.1:8001/api/research/status)
  if [[ "$R" != *"$RID"* ]]; then
    echo "finished after $((i*15))s"
    break
  fi
done
python3 -c "
import json
m = json.load(open('/Users/shitaosun/Project/AI-Personal/SignalForge/data/research/runs/$RID/report.json'))['metrics']
print('claims_by_verdict:', m['claims_by_verdict'])
print('sections_passed:', m['sections_passed'], '/', m['sections_total'])
print('validator_problems:', m['validator_problems'])
for d in m.get('validator_details', []):
    print(f\"  [{d['section_id']}] {d['heading'][:24]} passed={d['passed']}\")
    for p in d['problems'][:3]:
        print(f\"      {p['type']}: {p['detail'][:90]}\")
"
