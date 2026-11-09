#!/bin/zsh
curl -s -m 5 -o /dev/null -w 'research/status: %{http_code}\n' http://127.0.0.1:8001/api/research/status
curl -s -m 5 http://127.0.0.1:8001/api/research/status
echo
curl -s -m 5 -o /dev/null -w 'health: %{http_code}\n' http://127.0.0.1:8001/api/health
