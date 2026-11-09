#!/bin/zsh
cd /Users/shitaosun/Project/AI-Personal/SignalForge || exit 1
python3 - <<'PY'
import json, collections
d = json.load(open('data/research/runs/20261024-154813-a62448/report.json'))
probs = collections.Counter()
# report.json 没存 rejected 明细，从 metrics 只有计数；改看 verify 与 claims 的冲突分布
v = json.load(open('data/research/runs/20261024-154813-a62448/verify.json'))
conf = [x for x in v if x.get('verdict') == 'conflict']
print('conflict 簇:', len(conf))
for c in conf[:5]:
    print(f"  {len(c['claim_ids'])} claims, note={c.get('note','')[:60]}")
    for cid in c['claim_ids'][:2]:
        print(f"     {cid}")
print()
claims = {c['id']: c for c in json.load(open('data/research/runs/20261024-154813-a62448/claims.json'))}
for c in conf[:3]:
    print('--- 簇内论断 ---')
    for cid in c['claim_ids'][:4]:
        print(f"  [{cid}] {claims.get(cid,{}).get('text','')[:90]}")
PY
