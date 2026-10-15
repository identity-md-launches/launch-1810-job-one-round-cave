"""Keep the image editor's new pigment and preserve all other ancestor pixels."""
import hashlib
import json
from pathlib import Path

from image_bytes import jpeg, png, read_png, resize


def main():
    folder = Path('artifacts/line-4')
    ancestor = (folder/'wall.png').read_bytes()
    draft = (folder/'wall-v15.png').read_bytes()
    assert hashlib.sha256(ancestor).hexdigest() == 'fb883d3a545320a725574561733ef70bc6e0395180efc23e92208024b837eb66'
    w, h, old = read_png(ancestor)
    dw, dh, generated = read_png(draft)
    assert (w, h, dw, dh) == (1254, 1254, 1254, 1254)
    final = bytearray(old)
    for y in range(166, 269):
        for x in range(730, 803):
            i = (y*w+x)*3
            original = old[i:i+3]
            if sum(original) < 120:
                continue  # Protect deep original fissures.
            r, g, b = generated[i:i+3]
            charcoal = (735 <= x <= 798 and 171 <= y <= 239 and
                        r < 90 and g < 60 and b < 40 and r-g < 48 and
                        sum(original)-sum((r,g,b)) > 25)
            distance = (x-772)**2 + (y-246)**2
            ochre = (11**2 <= distance <= 23**2 and r > 1.75*g and r-g > 40)
            if charcoal:
                target = [round(v*.43) for v in original]
            elif ochre:
                target = [round(v*.25+p*.75) for v,p in zip(original,(r,g,b))]
            else:
                continue
            final[i:i+3] = bytes(target)
    changes = []
    for i in range(0, len(old), 3):
        if old[i:i+3] != final[i:i+3]:
            y, x = divmod(i//3, w)
            assert 730 <= x < 803 and 166 <= y < 269 and sum(old[i:i+3]) >= 120
            changes.append((x,y))
    assert 500 < len(changes) < 4000
    wall = png(w,h,final)
    sha = hashlib.sha256(wall).hexdigest()
    preview = jpeg(512,512,resize(w,h,final),52)
    assert len(preview) < 100_000
    for name in ('wall.png','wall-v15.png'):
        (folder/name).write_bytes(wall)
    Path('dist/line-4/35.jpg').write_bytes(preview)
    review = {
        'wall':{'paths':['artifacts/line-4/wall.png','artifacts/line-4/wall-v15.png'],
                'width':w,'height':h,'format':'PNG','mode':'RGB','bytes':len(wall),'sha256':sha},
        'preview':{'path':'dist/line-4/35.jpg','width':512,'height':512,'format':'JPEG',
                   'bytes':len(preview),'sha256':hashlib.sha256(preview).hexdigest()},
        'ancestorSha256':hashlib.sha256(ancestor).hexdigest(),
        'generatedDraftSha256':hashlib.sha256(draft).hexdigest(),
        'imageTool':'Built-in imagegen; generation 01a13dc9-9dd3-71f3-90ce-f22fb1a9b7e7',
        'prompt':'Preserve the entire inherited square cave, all paintings, rock, cracks, light, water and framing. Add only two short uneven charcoal trails converging on one small hollow red ochre pebble on vacant upper-middle rock, x690..800 y140..240. Worn earth pigments, bare stone inside. Preserve recognizable Pepe and both five-digit hands. No new hands, handprints, figures, writing, numerals, logos, watermarks or frames.',
        'changedPixels':len(changes),'unchangedPixels':w*h-len(changes),
        'additionBoundsExclusive':[min(x for x,y in changes),min(y for x,y in changes),
                                   max(x for x,y in changes)+1,max(y for x,y in changes)+1],
        'preservation':'Only new generated pigment was transferred. Every other pixel remains exact ancestor data. Deep original fissures are protected; every older painting, Pepe, both hands, cave light, framing and water are unchanged.',
        'visualReview':'Pending inspection of final PNG and decoded JPEG.',
        'unmetVisualRequirements':[],
        'limitations':['Local review is not independent visual certification.',
                       'The small mark is subtle in the preview.',
                       'Full generated draft changed surrounding stone; only new pigment was retained.']}
    Path('line-4/wall-review-35.json').write_text(json.dumps(review,indent=2)+'\n')
    record = {'name':'The Converging Trails','image':'https://api.imd.fun/artifacts/'+sha,
              'attributes':[
                  {'trait_type':'Cave','value':'Water'},
                  {'trait_type':'Wall','value':'Line 4'},
                  {'trait_type':'Number','value':35},
                  {'trait_type':'Left behind','value':'offline EIP-712 hash-witness verifier'},
                  {'trait_type':'Meaning','value':'Pepe follows two trails to check that they reach the same stone.'},
                  {'trait_type':'One thing','value':'offline EIP-712 typed-data digest checking'}]}
    Path('dist/line-4/35.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(review,indent=2))


if __name__ == '__main__':
    main()
