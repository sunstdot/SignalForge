#!/bin/zsh
cd /Users/shitaosun/Project/AI-Personal/SignalForge || exit 1
echo '--- GET report (known-good route) ---'
curl -s -m 8 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8001/api/research/runs/20261024-154813-a62448/report
echo '--- POST reverify ---'
curl -s -m 20 -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8001/api/research/runs/20261024-154813-a62448/reverify
echo '--- POST reverify body ---'
curl -s -m 20 -X POST http://127.0.0.1:8001/api/research/runs/20261024-154813-a62448/reverify | head -c 400
echo
echo '--- method check: GET on reverify path ---'
curl -s -m 8 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8001/api/research/runs/20261024-154813-a62448/reverify
