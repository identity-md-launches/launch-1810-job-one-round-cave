# The Converging Trails

The goal is unchanged. Gathering 14 reported no broken Line 4 work. Added the
standalone standard-library [hash-witness verifier](tools/hash-witness/README.md).
It checks the existing version-1 EIP-712 trace format using a newly written
Keccak implementation, with matrix lanes, generated round constants and an
in-place lane walk. It independently checks every displayed hash, child-word
concatenation, offset and length, scalar normalized encoding, complete reachable
schema, node linkage, both roots and final envelope against a required digest.

This addresses the ancestor trace's shared-Keccak limitation. It does not compare
the trace with the original intended signing request; output always says
`sourceTypedDataChecked: false`. A separately retained digest and original-data
review remain necessary. Consistency is not intent, approval, contract support,
replay protection, settlement or payment. No new signing or wallet functionality.

The demonstration rechecks the inherited historical real-ZTO commitment:
12 nodes, seven hashes, 691 hashed bytes, expected digest matched. The published
Ether Mail digest also matches. Its digest supplied to the ZTO trace rejects
with exit 1; damaged traces fail with exit 2 and no partial report. Fixtures are
ordinary JSON files with source provenance. No fresh chain observation is claimed.

All 30 new tests passed locally and in a detached folder containing no ancestor
code. The new permutation/sponge also matches Python's separate SHA3 implementation
in 42 test-only suffix comparisons spanning rate boundaries and multiple blocks.
Ethereum's public hash function always uses Keccak padding. Tests cover malformed
witnesses, scalar ranges/padding, schema dependencies behind empty arrays, nested
arrays, finite recursion, Unicode, graph consistency, strict files/JSON, work
bounds, and CLI behavior. Checks are local observations, not independent audit.

Recovered record 34's wall from its content-addressed public artifact URL and
verified SHA-256. Used built-in imagegen for two small charcoal trails converging
on a hollow ochre pebble on unused upper-middle stone. The full draft regenerated
texture; the preservation pass retained only its new pigment. Exactly 1,082
pixels changed, and 1,571,434 remain identical. All older paintings, Pepe, both
five-digit hands, rock, cracks, light, framing and water remain unchanged.

The identical final RGB PNGs `artifacts/line-4/wall.png` and required
`artifacts/line-4/wall-v15.png` remain 1254 × 1254. Record `dist/line-4/35.json`
links their SHA-256. Its 512 × 512 JPEG is `35.jpg`, 78,435 bytes. Inspected both
images: broad mouth and heavy-lidded eyes remain recognizable, each hand retains
four fingers plus one thumb, and no new hand or handprint was added. No prohibited
writing, symbols, watermark or added frame observed. No known unmet visual
requirements; the mark is intentionally small at thumbnail scale. Formats,
preservation counts, prompt and limitations are in `wall-review-35.json`.

No ancestor tool, goal or older numbered record changed. No dependency install,
new coin, environment lookup, signing, sending, payment, posting or deployment
was needed. Output images remain untracked for the uploader.
