#!/usr/bin/env python3
"""Transfer only new image-tool pigment onto untouched ancestral stone."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, resize, jpeg

ANCESTOR = 'f5b1343c09fcf96ad5901a1f6f0f14065af5588f5c867720eba1eee3ab1a14d9'
PROMPT = ('Preserve the ancestral square cave and all older marks. Add two small '
          'yellow ochre pebbles joined by a charcoal cord on vacant stone left '
          'above Pepe, one before the other. Worn earth pigments, no hands, '
          'letters, numbers, logos or borders.')


def main():
    ancestor_path = Path('artifacts/gathering/wall.png')
    target = Path('artifacts/gathering/wall-v15.png')
    ancestor, draft = ancestor_path.read_bytes(), target.read_bytes()
    assert hashlib.sha256(ancestor).hexdigest() == ANCESTOR
    w, h, old = read_png(ancestor)
    gw, gh, generated = read_png(draft)
    assert (w, h) == (gw, gh) == (1254, 1254)
    # Only new tool-drawn pigment is retained; regenerated stone is discarded.
    source = (395, 294, 498, 399)
    dest = (389, 300, 85, 87)
    x0, y0, width, height = dest
    final = bytearray(old)
    changed = 0
    for dy in range(height):
        for dx in range(width):
            sx = source[0] + dx * (source[2] - source[0]) // width
            sy = source[1] + dy * (source[3] - source[1]) // height
            si = (sy * w + sx) * 3
            r, g, b = generated[si:si+3]
            prior = old[si:si+3]
            charcoal = max(r, g, b) < 100 and max(prior) > 118
            ochre = (60 < r < 200 and r > 1.5*g and g > 1.7*b
                     and b/max(1, g) < prior[2]/max(1, prior[1]) - .08)
            if not (charcoal or ochre):
                continue
            oi = ((y0+dy)*w+x0+dx)*3
            rock = old[oi:oi+3]
            if max(rock) < 70:
                continue
            color = (44, 31, 19) if charcoal else (146, 89, 27)
            alpha = .73 if charcoal else .64
            for c in range(3):
                final[oi+c] = min(rock[c], round(rock[c]*(1-alpha)+color[c]*alpha))
            changed += final[oi:oi+3] != rock
    assert changed > 500
    for y in range(h):
        for x in range(w):
            i = (y*w+x)*3
            if not (x0 <= x < x0+width and y0 <= y < y0+height) or max(old[i:i+3]) < 70:
                assert final[i:i+3] == old[i:i+3]
    output = png(w, h, final)
    target.write_bytes(output)
    ancestor_path.write_bytes(output)
    preview = jpeg(512, 512, resize(w, h, final), quality=52)
    assert len(preview) <= 100000
    Path('dist/gathering/15.jpg').write_bytes(preview)
    review = {'ancestorSha256': ANCESTOR, 'ancestorSize': [w,h], 'wallSize': [w,h],
              'wallFormat': 'PNG', 'wallMode': 'RGB',
              'wallSha256': hashlib.sha256(output).hexdigest(),
              'generatedDraftSha256': hashlib.sha256(draft).hexdigest(),
              'generatedDraftRetained': False, 'sourceRectangle': list(source),
              'additionRectangle': list(dest), 'changedPixels': changed,
              'unchangedPixels': w*h-changed, 'allPixelsOutsideAdditionUnchanged': True,
              'deepCracksProtected': True, 'previewSize': [512,512],
              'previewFormat': 'JPEG', 'previewBytes': len(preview),
              'imageTool': 'image_gen.imagegen', 'prompt': PROMPT,
              'reviewStatus': 'requires final visual inspection', 'unmetVisualRequirements': []}
    Path('gathering/wall-review-15.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(review,indent=2))


if __name__ == '__main__':
    main()
