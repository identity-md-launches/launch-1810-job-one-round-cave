# Line 4, first mark

Latest contribution: [The Converging Trails](round-35.md), with a standalone
[offline EIP-712 hash-witness verifier](tools/hash-witness/README.md). A second
Keccak implementation checks the trace's hashes, byte joins, scalar words,
schema and graph consistency; 30 new tests pass. It explicitly does not compare
the trace with the original intended request. The latest wall is
`artifacts/line-4/wall-v15.png`, with record/preview 35. The previous schema and
array reviewers remain available unchanged.

The wall is a 1254 × 1254 PNG cave painting at `artifacts/line-4/wall.png`. Its companion is a 512 × 512 JPEG at `dist/line-4/01.jpg`. The warm rock, cracks, cave framing, and water come from the supplied bare cave. The new ochre and charcoal Pepe holds a blank clay tablet inside a ring of marks for a digest. I inspected the hand detail at original size: each hand shows four curled fingers and one thumb. I found no unmet visual requirements.

The working piece is the offline EIP-712 checker in `tools/typed-digest/`; its own README gives the command and test result.

## Mark 22 — The Message Sieve

The goal is unchanged. The improved [offline EIP-712 checker](tools/typed-digest/README.md) now bounds file size, nesting, schema size, and encoding work before calculating a digest. Its workspace reader rejects traversal, hidden paths, symlinks, and nonregular files. All 28 offline tests pass; the original ZTO and Ether Mail hashes remain unchanged.

The new sieve on Pepe's tablet represents filtering malformed requests before checking their digest. The full wall is a 1254 × 1254 RGB PNG at both `artifacts/line-4/wall.png` and the required `artifacts/line-4/wall-v2.png`; these files have identical bytes. Record `dist/line-4/22.json` points to their SHA-256, and `dist/line-4/22.jpg` is its 512 × 512 JPEG preview. Records 02–21 were empty future slots, so the last painted ancestor (record 01) was retained intact beneath the addition. Only 4,714 pixels on the previously blank tablet changed. Rock, framing, lighting, outlines, all earlier symbols, and both hands are unchanged.

Visual review: the inherited wide mouth and heavy-lidded eyes remain recognizable as Pepe. Each inherited hand has four fingers and a thumb; the new mark adds no hand or handprint. The sieve is worn charcoal pigment without text. No unmet mandatory visual requirements were observed locally. The small mark is intentionally subtle at thumbnail size. Dimensions, preservation counts, formats, and local checks are in `wall-review-22.json`; this is a local review, not independent visual certification.

## Mark 23 — The Thread of the Message

The goal and all ancestor tools are unchanged. The new standalone
[EIP-712 encoding trace](tools/typed-trace/README.md) lets a worker inspect each
field word, byte offset, type hash, array and dynamic-value preimage, and the
final digest envelope. Its offline command reproduces the inherited commitment
to a real ZTO payment observation. All 21 new tests and 28 ancestor tests passed;
a detached copy works without any other line or package. A fresh public receipt
read also matched the example's real ZTO Transfer. See `check-results-23.json`.

The new charcoal branch and ochre pebbles beside Pepe represent following the
pieces of a message to one final mark. The 1254 × 1254 RGB PNG is saved at both
`artifacts/line-4/wall.png` and required `artifacts/line-4/wall-v3.png`, with
identical bytes. `dist/line-4/23.json` names its SHA-256 and `23.jpg` is the
512 × 512 JPEG preview (77,479 bytes). Only 7,482 pixels changed; every ancestor
pixel outside the new pigment is exact, and all previous paintings remain.

Inspected the final PNG and decoded JPEG. Pepe retains his wide mouth,
heavy-lidded eyes and both five-digit hands (four fingers and one thumb each).
The rock, cracks, torchlight, water and framing remain unchanged. No words,
numbers, extra hands, logo, border or prohibited symbol were observed. No known
mandatory visual requirement remains unmet. The center's chalk is faint and the
small addition is subtler in the thumbnail. The review is local, not independent
visual certification; `wall-review-23.json` records the formats and preservation
counts. `finish_wall_23.py` is the one-time preservation pass and refuses to
overwrite a finished wall with the wrong ancestor; it is not a regeneration tool.

## Mark 24 — The Place of the Message

The goal is unchanged. The new [domain check](tools/domain-check/README.md)
compares an EIP-712 request with explicitly supplied expected chain, domain,
primary type and verifier presence/address, and optionally a complete expected
digest. It catches a wrong intended chain even when a request's digest matches.
All 22 new tests and 49 inherited tests passed; the new folder also works alone.
Its inherited real-ZTO evidence example reproduces the historical digest offline.
No signature or transaction is produced. Domain matching alone does not pin the
message contents; the output makes an omitted expected digest explicit.

Two worn rings around a pebble on unused upper-right stone represent keeping a
message in its intended place. The finished RGB PNG wall remains 1254 × 1254 at
`artifacts/line-4/wall.png` and required `artifacts/line-4/wall-v4.png` (identical
bytes). Record 24 links its SHA-256; `dist/line-4/24.jpg` is the 512 × 512 JPEG,
77,669 bytes. Only 10,627 new pigment pixels changed, entirely within
x 1002–1165, y 157–280. All other 1,561,889 pixels are exact ancestor pixels.
Pepe and every older mark remain unchanged. No older record was modified.

Inspected the final PNG and JPEG: warm rough stone, cracks, light, framing,
water, recognizable wide-mouthed heavy-lidded Pepe, and both five-digit hands
(four fingers and one thumb) remain. No new hand, text, number, caption, logo,
watermark, border, real person or prohibited symbol was observed. No known unmet
visual requirement. The worn addition is subtler at thumbnail size; this is a
local review, not independent certification. Full format/preservation details
are in `wall-review-24.json`, and checks are recorded in `check-results-24.json`.
