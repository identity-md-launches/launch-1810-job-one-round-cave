#!/usr/bin/env python3
"""Check portability and rejection behavior without changing a line folder."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
BASE = 'shared/ordered-settlement/'
PIN = '70e3848cd1ae7417abbd8ca0b05e4cb271a485978ab0921420270911672ef7de'
DEMO = [BASE+'review.py', BASE+'plan.json', '--sha256', PIN]


def main():
    assert Path.cwd() == ROOT
    scratch = ROOT/'test/scratch/round15'
    scratch.mkdir(parents=True, exist_ok=True)
    detached = scratch/'portable'
    shutil.copytree(ROOT/BASE, detached/BASE, dirs_exist_ok=True)
    plan = json.loads((ROOT/BASE/'plan.json').read_bytes())
    reverse = json.loads(json.dumps(plan)); reverse['sequence'].reverse()
    malformed = json.loads(json.dumps(plan)); malformed['batch']['items'][0]['policy']['requireFinalized'] = 'yes'
    inputs = []
    for name, value in [('reverse', reverse), ('malformed', malformed)]:
        path = scratch/(name+'.json'); raw=(json.dumps(value)+'\n').encode();path.write_bytes(raw)
        inputs.append([BASE+'review.py', str(path.relative_to(ROOT)), '--sha256', hashlib.sha256(raw).hexdigest()])
    cases = [
        (ROOT, 0, [BASE+'test_review.py'], None),
        (ROOT, 0, DEMO, BASE+'example-match.json'),
        (ROOT, 1, inputs[0], BASE+'example-order-rejection.json'),
        (ROOT, 1, inputs[1], BASE+'example-structure-rejection.json'),
        (detached, 0, [BASE+'test_review.py'], None),
        (detached, 0, DEMO, None),
        (ROOT, 2, ['line-2/tools/jsonl-contract/check.py', 'line-2/tools/json-contract/report.contract.json',
                   'line-2/tools/jsonl-contract/mixed-reports.jsonl'], 'gathering/mixed-reports-15.json'),
        (ROOT, 1, ['line-4/tools/hash-witness/hash_witness.py', 'line-4/tools/hash-witness/zto-trace.json',
                   '--expect', '0xbe609aee343fb3c4b28e1df9e632fca64fcfaede20f02e86244efddf30957bd2'], None),
        (ROOT, 1, ['line-1/tools/snapshot-integer/decode.py', 'line-1/tools/snapshot-integer/live-zto.json',
                   '--encoding', 'quantity'], None),
    ]
    rows = []
    for cwd, expected, args, save in cases:
        done = subprocess.run([sys.executable, '-B', *args], cwd=cwd, capture_output=True,
                              text=True, timeout=45, env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
        row = {'command':['python3','-B',*args], 'detached':cwd != ROOT,
               'expectedExit':expected,'exitCode':done.returncode,'passed':done.returncode == expected,
               'stdout':done.stdout,'stderr':done.stderr}
        rows.append(row)
        if save and row['passed']:
            assert len(done.stdout.encode()) <= 100000
            (ROOT/save).write_text(done.stdout)
        print('PASS' if row['passed'] else 'FAIL', args[0], done.returncode)
    raw = json.dumps(rows, indent=2)+'\n'
    assert len(raw.encode()) <= 100000
    (ROOT/'gathering/round-checks-15.json').write_text(raw)
    return 0 if all(r['passed'] for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
