"""Offline structural delivery check; visual review is recorded separately."""
import hashlib
import json
from pathlib import Path
import subprocess

from image_bytes import read_png


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def jpeg_dimensions(raw):
    assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9'
    offset = 2
    while offset < len(raw):
        assert raw[offset] == 255
        marker = raw[offset+1]
        size = int.from_bytes(raw[offset+2:offset+4], 'big')
        if marker == 0xc0:
            return (int.from_bytes(raw[offset+7:offset+9], 'big'),
                    int.from_bytes(raw[offset+5:offset+7], 'big'))
        assert marker != 0xda and size >= 2
        offset += 2 + size
    raise AssertionError('no baseline JPEG frame')


def main():
    def git(*args):
        return subprocess.check_output(['git', *args])

    records = sorted(Path('dist/line-4').glob('*.json'))
    assert len(records) == 35
    record = json.loads(Path('dist/line-4/35.json').read_bytes())
    assert set(record) == {'name','image','attributes'}
    traits = record['attributes']
    assert all(set(t) == {'trait_type','value'} for t in traits)
    assert [t['trait_type'] for t in traits] == ['Cave','Wall','Number','Left behind','Meaning','One thing']
    assert traits[0]['value'] == 'Water' and traits[1]['value'] == 'Line 4'
    assert type(traits[2]['value']) is int and traits[2]['value'] == 35
    for old in records:
        if old.name != '35.json':
            assert git('show','HEAD:'+str(old)) == old.read_bytes(), old
    tracked_dist = git('ls-files','dist/line-4').decode().splitlines()
    for name in tracked_dist:
        assert git('show','HEAD:'+name) == Path(name).read_bytes(), name
    goal = Path('line-4/GOAL.md').read_bytes()
    assert git('show','HEAD:line-4/GOAL.md') == goal
    wall = Path('artifacts/line-4/wall-v15.png').read_bytes()
    assert wall == Path('artifacts/line-4/wall.png').read_bytes()
    width,height,pixels = read_png(wall)
    assert (width,height,len(pixels)) == (1254,1254,1254*1254*3)
    assert record['image'] == 'https://api.imd.fun/artifacts/'+sha(wall)
    preview = Path('dist/line-4/35.jpg').read_bytes()
    assert jpeg_dimensions(preview) == (512,512) and len(preview) < 100_000
    review = json.loads(Path('line-4/wall-review-35.json').read_bytes())
    assert review['wall']['sha256'] == sha(wall)
    assert review['preview']['sha256'] == sha(preview)
    assert review['unmetVisualRequirements'] == [] and 'Pending' not in review['visualReview']
    checks = json.loads(Path('line-4/check-results-35.json').read_bytes())
    assert checks['allPassed'] and all(c['passed'] for c in checks['checks'])
    source = Path('line-4/tools/hash-witness')
    provenance = json.loads((source/'provenance.json').read_bytes())
    for name,expected in provenance['sourceFiles'].items():
        assert sha(Path(name).read_bytes()) == expected
    for name,expected in provenance['fixtureSha256'].items():
        assert sha((source/name).read_bytes()) == expected
    modified = git('diff','--name-only').decode().splitlines()
    untracked = git('ls-files','--others','--exclude-standard').decode().splitlines()
    delivered = modified + untracked
    prefixes = ('line-4/','dist/line-4/','artifacts/line-4/')
    assert all(p.startswith(prefixes) for p in delivered), delivered
    for name in delivered:
        if not name.startswith('artifacts/'):
            assert Path(name).stat().st_size <= 100_000, name
    assert not git('ls-files','artifacts/line-4/wall.png','artifacts/line-4/wall-v15.png')
    report = {'passed':True,'recordCount':len(records),'number':35,'olderRecordsAndPreviewsUnchanged':True,
              'goalUnchanged':True,'goalSha256':sha(goal),'scopeChecked':True,
              'sourceAndFixtureProvenanceMatches':True,'allLocalChecksPassed':True,
              'wall':review['wall'],'preview':review['preview'],
              'unmetVisualRequirements':review['unmetVisualRequirements'],
              'limitations':'Structural checks and local tests do not certify appearance, cryptographic correctness or source-request equivalence.'}
    Path('line-4/delivery-check-35.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
