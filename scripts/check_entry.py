#!/usr/bin/env python3
"""Lightweight offline structural entry check; not a substitute for the official PLE kit."""
from pathlib import Path
import re, sys
root=Path(__file__).resolve().parents[1]
checks=[]
def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
sub=(root/'submission.yaml').read_text()
check('submission.yaml exists', (root/'submission.yaml').is_file())
check('entry name format', bool(re.search(r'^name:\s*[a-z0-9][a-z0-9-]{1,38}\s*$',sub,re.M)))
models={'google-cloud/gemini-4-argon','google-cloud/gemini-4-carbon','google-cloud/gemini-4-neon','google-cloud/gemini-4-hydrogen','google-cloud/gemini-3.8-flash','google-cloud/gemini-3.1-pro-preview','google-cloud/claude-opus-5-5','google-cloud/gpt-oss-120b','google-cloud/glm-5.2','google-cloud/gemma-4-26b','google-cloud/llama-4-maverick'}
api=re.search(r'^model_api:\s*(\S+)',sub,re.M)
check('model_api is listed by competition guide', bool(api and api.group(1) in models), api.group(1) if api else 'missing')
check('serve.py present', (root/'serve.py').is_file())
check('harness.py present', (root/'harness.py').is_file())
check('requirements pinned', all(re.search(r'==',line) for line in (root/'requirements.txt').read_text().splitlines() if line.strip()))
check('MIT license', 'MIT License' in (root/'LICENSE').read_text())
check('AGENTS instructions present', (root/'AGENTS.md').is_file())
check('tests present', (root/'tests_smoke.py').is_file() and (root/'tests_unit.py').is_file() and (root/'tests_context.py').is_file() and (root/'tests_cancel.py').is_file())
check('no artifacts falsely generated', not (root/'artifacts').exists(), 'Expected until official dev evaluation is run')
check('cover image present', (root/'media'/'cover.jpg').is_file())
check('architecture figure present', (root/'figures'/'architecture.png').is_file())
check('score-cost figure present', (root/'figures'/'score_vs_cost.png').is_file())
check('failure figure present', (root/'figures'/'failure_breakdown.png').is_file())
report=root/'writeup'/'PLE_WRITEUP.md'
if report.exists():
    words=len(report.read_text().split())
    check('writeup below 2000-word cap', words<=2000, f'{words} words (draft, not submission-ready)')
else: check('writeup draft present', False)
for n,ok,d in checks: print(('PASS' if ok else 'FAIL'), n, ('— '+d if d else ''))
print(f'\n{sum(ok for _,ok,_ in checks)}/{len(checks)} local static checks passed.')
if not all(ok for _,ok,_ in checks): sys.exit(1)
