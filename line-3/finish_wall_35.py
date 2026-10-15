"""Composite the generated, isolated pigment mark onto vacant ancestral rock."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, resize, jpeg

ROOT = Path(__file__).resolve().parent.parent
ANCESTOR = '85f1f89bbc57722d8436a6617b58c9f4725043fa10e5300b84e650405da7b803'
PROMPT = ('Two irregular red-ochre stepping stones arranged diagonally, joined by an uneven '
          'rising charcoal trail. Isolated worn Lascaux pigment on white. No text, arrows, '
          'hands, footprints, digits, logos, numbers, borders or frames.')


def main():
    wall = ROOT / 'artifacts/line-3/wall.png'
    target = ROOT / 'artifacts/line-3/wall-v15.png'
    ancestor = wall.read_bytes()
    assert hashlib.sha256(ancestor).hexdigest() == ANCESTOR
    w, h, old = read_png(ancestor)
    draft = target.read_bytes()
    gw, gh, generated = read_png(draft)
    assert (w, h) == (1254, 1254) and gw > 0 and gh > 0

    def pigment(x, y):
        r, g, b = generated[(y*gw+x)*3:(y*gw+x)*3+3]
        return max(r, g, b) < 185 or (r > g*1.12 and g > 85 and b < g*.8)

    points = [(x,y) for y in range(gh) for x in range(gw) if pigment(x,y)]
    sx0, sy0 = min(x for x,y in points), min(y for x,y in points)
    sx1, sy1 = max(x for x,y in points)+1, max(y for x,y in points)+1
    # Vacant rock beside Pepe's face, below the ancestral diagonal staff.
    x0, y0, width, height = 674, 408, 89, 86
    final = bytearray(old)
    changed = 0
    for dy in range(height):
        for dx in range(width):
            x, y = x0+dx, y0+dy
            i = (y*w+x)*3
            rock = old[i:i+3]
            if max(rock) < 85:
                continue
            xa = sx0+dx*(sx1-sx0)//width
            xb = sx0+(dx+1)*(sx1-sx0)//width
            ya = sy0+dy*(sy1-sy0)//height
            yb = sy0+(dy+1)*(sy1-sy0)//height
            total = [0,0,0]
            coverage = 0
            for gy in range(ya,yb):
                for gx in range(xa,xb):
                    if not pigment(gx,gy):
                        continue
                    r,g,b = generated[(gy*gw+gx)*3:(gy*gw+gx)*3+3]
                    chosen = ((157,76,36) if r > g*1.12 and g > 85 and b < g*.8 else (53,42,31))
                    for c in range(3):
                        total[c] += chosen[c]
                    coverage += 1
            if not coverage:
                continue
            alpha = .83*coverage/((xb-xa)*(yb-ya))
            light = min(1.16,max(.64,sum(rock)/(3*139)))
            for c in range(3):
                final[i+c] = round(rock[c]*(1-alpha)+total[c]/coverage*light*alpha)
            changed += final[i:i+3] != rock
    assert changed > 500
    for y in range(h):
        for x in range(w):
            i = (y*w+x)*3
            if not (x0 <= x < x0+width and y0 <= y < y0+height) or max(old[i:i+3]) < 85:
                assert final[i:i+3] == old[i:i+3]
    encoded = png(w,h,final)
    target.write_bytes(encoded)
    wall.write_bytes(encoded)
    thumbnail = resize(w,h,final)
    quality = 52
    preview = jpeg(512,512,thumbnail,quality)
    while len(preview) > 100000 and quality > 10:
        quality -= 5
        preview = jpeg(512,512,thumbnail,quality)
    assert len(preview) <= 100000
    (ROOT/'dist/line-3/35.jpg').write_bytes(preview)
    review = {'ancestorSha256': ANCESTOR, 'ancestorDimensions':[w,h],
              'wallDimensions':[w,h], 'wallFormat':'PNG', 'wallMode':'RGB',
              'wallSha256':hashlib.sha256(encoded).hexdigest(),
              'generatedDraftSha256':hashlib.sha256(draft).hexdigest(),
              'draftRetained':False, 'additionRectangle':[x0,y0,width,height],
              'changedPixels':changed, 'unchangedPixels':w*h-changed,
              'allPixelsOutsideAdditionUnchanged':True, 'deepCracksProtected':True,
              'previewDimensions':[512,512], 'previewFormat':'JPEG',
              'previewBytes':len(preview), 'previewQuality':quality,
              'imageTool':'image_gen__imagegen', 'prompt':PROMPT,
              'reviewStatus':'requires visual inspection', 'unmetVisualRequirements':[]}
    (ROOT/'line-3/wall-review-35.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(review,indent=2))


if __name__ == '__main__':
    main()
