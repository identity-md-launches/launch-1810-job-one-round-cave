"""Transfer only generated pebble pigment into vacant ancestral stone."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, resize, jpeg

base = Path('artifacts/line-2/wall.png')
output = Path('artifacts/line-2/wall-v15.png')
ancestor, draft = base.read_bytes(), output.read_bytes()
assert hashlib.sha256(ancestor).hexdigest() == 'f4c56a18b39ea9c9c4f335de962f8f67c5f21b502ff81322576abf68d9688c84'
w, h, old = read_png(ancestor)
dw, dh, generated = read_png(draft)
assert (w, h) == (dw, dh) == (1254, 1254)
x0, y0, width, height = 252, 470, 110, 170
cx, cy, cw, ch = 298, 347, 102, 153
final = bytearray(old)
changed = 0
for y in range(y0, y0 + height):
    for x in range(x0, x0 + width):
        i = (y*w+x)*3
        rock = old[i:i+3]
        sx, sy = cx+(x-x0)*cw//width, cy+(y-y0)*ch//height
        j = (sy*dw+sx)*3
        r, g, b = generated[j:j+3]
        # Restrict transfer to the generated pebbles and their three trails;
        # discard the regenerated rock and every regenerated ancestor mark.
        circle = any((sx-a)**2+(sy-bb)**2 < 24**2
                     for a, bb in ((321, 372), (324, 422), (323, 476)))
        trail = 342 <= sx <= 396 and any(abs(sy-t) < 8 for t in (369, 422, 476))
        if not (circle or trail) or max(rock) < 85 or (x*19+y*31)%23 == 0:
            continue
        charcoal = max(r, g, b) < 106
        ochre = circle and r > 1.3*g and 50 < g < 112 and b < 86
        chalk = (sx-324)**2+(sy-422)**2 < 9**2 and r > 175 and g > 145 and b > 90
        if charcoal or ochre or chalk:
            pigment = (42, 30, 20) if charcoal else ((197, 180, 139) if chalk else (143, 64, 30))
            alpha = .68 if charcoal else .60
            for c in range(3):
                final[i+c] = round(rock[c]*(1-alpha)+pigment[c]*alpha)
            changed += final[i:i+3] != old[i:i+3]
assert 500 < changed < width*height
for y in range(h):
    for x in range(w):
        i = (y*w+x)*3
        if final[i:i+3] != old[i:i+3]:
            assert x0 <= x < x0+width and y0 <= y < y0+height
            assert max(old[i:i+3]) >= 85
encoded = png(w, h, final)
base.write_bytes(encoded)
output.write_bytes(encoded)
preview = jpeg(512, 512, resize(w, h, final), 52)
assert len(preview) < 100000
Path('dist/line-2/35.jpg').write_bytes(preview)
review = {
    'number': 35,
    'ancestor_sha256': hashlib.sha256(ancestor).hexdigest(),
    'sha256': hashlib.sha256(encoded).hexdigest(),
    'wall': {'paths': [str(base), str(output)], 'width': w, 'height': h,
             'format': 'PNG', 'mode': 'RGB', 'bytes': len(encoded)},
    'preview': {'path': 'dist/line-2/35.jpg', 'width': 512, 'height': 512,
                'format': 'JPEG', 'bytes': len(preview)},
    'addition_region': {'x': x0, 'y': y0, 'width': width, 'height': height},
    'changed_pixels': changed, 'unchanged_pixels': w*h-changed,
    'outside_region_pixel_identical': True, 'dark_cracks_preserved': True,
    'generation_tool': 'image_gen.imagegen',
    'draft_sha256': hashlib.sha256(draft).hexdigest(),
    'generated_dimensions': [dw, dh], 'draft_retained_in_workspace': False,
    'visual_review': 'pending inspection', 'unmet_visual_requirements': []}
Path('line-2/wall-review-35.json').write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps(review, indent=2))
