# Water gathering 15 — The Ordered Pebbles

All **142 offline check/demo commands passed**, covering **1,111 unittest cases**
(one inherited auxiliary HTTP-server test skipped; its memory-backed boundary
checks ran). Nine supplementary trials matched their expected exits. The new
shared integration's **15 tests** passed both here and in a detached workspace.
These are local observations, not independent certification. No line folder
changed: every line file's before/after SHA-256 matches.

Sources were read and parsed before execution, with file, transport, subprocess
and mutation operations reviewed. The operation inventory covers 203 Python
files, including shared dependencies; it is an aid to review, not a security
proof. Source-writing Line 4 suites ran from exact scratch copies, including
schema-review. Evidence: `source-review-15.json`, `source-review-15-shared.json`,
`check-15-line-{1,2,3,4}.json`, `check-15-shared.json`, `check-console-15.txt`,
`round-checks-15.json`, `line-source-hashes-15.json`, `delivery-check-15.json`.
Group reports overlap where shared commands mention line inputs; 142 is the
unique command count.

## Line 1 — portable Ethereum snapshots

**Tried:** every tool's inherited offline demo/check, including bounded/safe
capture files, anchored and hash-pinned ZTO, comparisons, reports, revisits,
batches, provider agreement, retained pins, generic diff, response correlation,
selection and the new integer decoder. New decoder tests and both documented
demos passed. An explicit wrong interpretation was also tried.

**Works:** the new tool decodes the retained real ZTO totalSupply word to exactly
**1000000000000000000000000000 raw**, formatted at caller-supplied scale 18 as
**1000000000.000000000000000000**. Quantity selection from the saved block gives
**26195002**. Choosing quantity encoding for the zero-padded ABI supply word
correctly rejects with exit 1. Signed/unsigned interpretation, canonical quantity
syntax, exact integer scaling and CLI/file/response boundaries pass the suite.

**Broken / limits:** no exercised failure. The saved `latest` supply observation
is historical and has no recorded block anchor. Explicit scaling does not prove
token decimals; a checksum does not authenticate a provider. A consistently
resealed fabricated observation can pass validation, as its tests demonstrate.
Integer interpretation alone does not prove ABI type, balance, price or payment.
No fresh RPC capture was made this gathering.

**Goal / scope:** useful for arbitrary workers handling Ethereum RPC observations,
not cave records. It differs from Line 3's settlement decision. Already useful
within 21 steps; retain explicit decoding and bounded evidence. A general ABI
platform, indexer or state-proof engine would need a narrower separate brief.

## Line 2 — explicit JSON contracts and diagnostics

**Tried:** every inherited contract/check demo and suite: basic, ordered, batch,
bounded, repair/change, rule/source locators, guards/context, HTML and SARIF.
New JSON Lines checker: saved ZTO policy, its 18 tests and malformed mixed batch.

**Works:** ZTO-first/IMD-second policy JSONL passes with exit 0. Mixed input exits
**2**, reports **four rows: two pass, one has three structural violations, one
is malformed**, and still checks the fourth row. Actual output is retained in
`mixed-reports-15.json`. Exact whole-file byte/character positions, CRLF/Unicode,
row recovery, scalar inputs, independent pins, strict parsing, bounded complete
output and immutable inputs pass. `complete: true` correctly coexists with
`valid: false`; completion alone is not acceptance.

**Broken / limits:** no exercised failure. Deliberate contract subset, not full
JSON Schema. Rows are independent; no cross-row uniqueness or business semantics.
At most 256 rows and 100 KB complete output; this is bounded in-memory checking,
not a streaming service. Trusted regexes and file limits do not form a CPU
sandbox. Structural validity does not establish truth or permission.

**Goal / scope:** generally useful for API exports, queues and worker manifests.
Distinct from Line 4's encoding/cryptographic review. The goal already has useful
bounded implementations; full schema compatibility and automatic semantic repair
would exceed the remaining useful scope. Keep exact diagnostics and explicit rules.

## Line 3 — Ethereum transaction settlement

**Tried:** all inherited settlement/payment, discovery, RPC boundary, agreement,
recheck, freshness, ancestry, position, pin, batch and plan-diff checks. New
settlement-order demo and all **24 tests** passed. Shared trials also require
structure, complete membership and ordering after full batch replay.

**Works:** the real saved ZTO transactions
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`
and `0x64847acc0a0d6b0a5cf61cfb26fea3ccfae61a75916ff9d01453a6c7a17b47d7`
pass in their intended order: block/index **26190898/181**, then **26194715/146**.
Both policies require 12 confirmations and finality. Reversing the required
sequence correctly refuses despite both transactions meeting settlement policy.
Plan pin precedes parsing; evidence pins precede replay. Missing/duplicate/case-
aliased members, slot collisions, inconsistent counts, conflicting sampled
anchors, unavailable evidence and malformed policies are covered by tests.

**Broken / limits:** no exercised failure. Chronological position does not prove
causation or application prerequisites. Provider assertions are not consensus,
trie or full inter-block ancestry proofs. Full transaction lists are checked
within each transcript, not compared in full across transcripts. No current
freshness, amount, ownership, authorization or persistent deduplication follows.
Bundled hashes demonstrate retention and are not independent custody.

**Goal / scope:** useful beyond this cave and distinct from generic capture.
Already bounded and working. Keep explicit transaction/policy/evidence decisions;
a persistent accounting service, unattended monitor or universal workflow engine
would need narrowing to a separate task.

## Line 4 — independent EIP-712 digest review

**Tried:** all inherited digest/trace, domain, request/set, pin/change, string,
integer, bytes, schema and array checks. New hash-witness verifier: real historical
ZTO trace, published Ether Mail fixture, **30 tests**, plus wrong-digest rejection.

**Works:** ZTO witness validates against
`0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774`;
**12 nodes, 7 hashes and 691 hash-input bytes** checked. Ether Mail matches
`0xbe609aee343fb3c4b28e1df9e632fca64fcfaede20f02e86244efddf30957bd2`.
Using the Mail expectation for ZTO exits 1 with a consistent witness but a digest
mismatch. The new verifier uses a second Keccak implementation, instead of
importing an ancestor encoder. Published vectors, 42 test-only SHA3 comparisons,
trace graph/schema/word validation, boundaries and disabled transport pass.

**Broken / limits:** no exercised failure. The verifier explicitly reports
`sourceTypedDataChecked: false`: a consistent trace is not the intended source
request. Shared fixture ancestry is not independent semantic approval. Unused
source declarations absent from a trace cannot be checked here. The new
cryptographic implementation has not received an independent audit. A matching
digest does not establish signer intent, protocol support, authorization,
freshness or payment. The ZTO message is illustrative evidence commitment, not
a token signing interface or fresh transaction.

**Goal / scope:** general typed-data review, distinct from structural validation
and settlement. Independent hashing is meaningful progress toward the stated
goal. Keep exact offline interpretation and separately controlled expectations;
wallet integration or signing automation is unnecessary for the 21-step goal.

## Shared — ordered settlement review

New `shared/ordered-settlement/` joins Line 2's contract diagnostics to Line 3's
pinned order-plan, full batch settlement and position checks. Seven unchanged
Python sources and two real ZTO evidence fixtures are ordinary files, with
source hashes in `provenance.json`. The complete folder runs offline without
line folders, installation, accounts or configuration. Its README gives a single
working command, evidence, output interpretation, relocation and limitations.

The fixed structural contract locates malformed policy fields by JSON Pointer;
an incoming plan cannot select a weaker contract. Plan pin is verified before
parsing. Structural and semantic membership/path/policy checks precede evidence;
replay consumes exactly the captured bytes that were checked. All evidence must
match pins and pass settlement/position review before the sequence is evaluated.
No partial success grants acceptance and no expected hash is auto-updated.

Historical ZTO demo: `accepted: true`, `settlement_order_match`. Reversed sequence:
exit 1, `order_review_required`, although the embedded batch is accepted. Wrong
policy type: exit 1 with `/batch/items/0/policy/requireFinalized`, without opening
evidence. Actual reports are beside the tool. All **15 integration tests** and
the demo pass in a detached workspace containing only this shared folder.

This adds an explicit intended-order check, not a business workflow or payment
service. Existing `shared/settlement-gate` still handles non-weakening policy
comparison against a retained baseline; the new tool does not silently merge
that distinct policy. Line 4 can separately review a typed commitment; nothing
here grants permission to sign it. Independently retained plan hashes and
policies remain necessary. Replacing both a plan and its hash defeats protection.

## Coins and deployment

`COINS.md`: **none**. All four lines and shared tools already exist without a
new coin; retained real Ethereum examples use ZTO first, IMD second. No
indispensable new hook behavior or contract needing Sepolia was identified.
No coin/deployment order or request-check POST. Nothing was signed, sent, paid,
posted or deployed; no key, wallet, secret or environment lookup was used.

## Wall, record and gallery

Gathering **15**, a continuation. Downloaded ancestor 14 by its numbered record
and verified exact SHA-256 before editing. The built-in image tool generated
linked ochre pebbles on vacant rock left above the central Pepe. It regenerated
surrounding stone too; only its new pigment was retained. **2,226 pixels** gained
pigment inside x **389–473**, y **300–386**; **1,570,290 pixels** remain exactly
ancestral. All pixels outside this patch and deep cracks inside remain identical.
The patch contains no older painting. Older marks, framing, rock and torchlight
are preserved. The pebbles mean keeping linked evidence in its intended order.

`artifacts/gathering/wall-v15.png` and identical `wall.png`: **1254 × 1254 RGB PNG**,
SHA-256 `bed3ef034cdc0ac958c698188b2661cec12ce8a63809600fa85c1a7c044f1769`.
`dist/gathering/15.jpg`: **512 × 512 JPEG**, **76,203 bytes**. Numbered JSON has
exactly the required shape/traits and references that final PNG hash.
Full PNG and decoded JPEG were visually inspected. Central Pepe's wide mouth
and heavy-lidded eyes remain. No new hands or handprints: zero new digits to
count. No letters, numbers, captions, signatures, logos, watermarks, borders,
frames, real people, political or hateful symbols observed. **No known unmet
visual requirements.** Dimensions, formats, prompt, preservation and review are
recorded in `wall-review-15.json`. Structural checks do not certify appearance.

`dist/goals.json` matches the four GOAL.md files verbatim after trimming.
The one-page gallery includes all **161 records: 75 paintings, 86 placeholders**,
by wall, painted newest first, with future records in collapsible lists. Inline
styles/captions, local JPEG previews and public full-wall links; **98,393 bytes**.
This is not the first gathering; inherited future placeholder records remain
intact and only gathering slot 15 was replaced. Every required 01..21 slot exists.

## Delivery

`python3 -B gathering/check_delivery_15.py` passes actual PNG/JPEG bytes, hash and
record shape, gallery ordering/coverage, goals, all file limits, old/new shared
vendor provenance and complete line-folder immutability. `git diff --check`
passes. All changes are ordinary files in allowed gathering/shared/dist paths;
required PNG remains unstaged for the separate uploader. No dependencies were
installed and no configuration or line folders were changed.
