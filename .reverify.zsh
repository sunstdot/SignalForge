#!/bin/zsh
RID=20261024-154813-a62448
echo '--- before ---'
python3 -c "
import json
d = json.load(open('/Users/shitaosun/Project/AI-Personal/SignalForge/data/research/runs/$RID/report.json'))
print(d['metrics']['claims_by_verdict'])
"
echo '--- trigger reverify ---'
curl -s -m 15 -X POST "http://127.0.0.1:8001/api/research/runs/$RID/reverify"
echo
echo '--- status ---'
sleep 3
curl -s -m 10 http://127.0.0.1:8001/api/research/status
