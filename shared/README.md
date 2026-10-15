# Shared pieces

[RPC evidence bridge](rpc-evidence/README.md) combines line 1's capture format
and line 2's structural checker. It includes vendored standard-library code,
a real mainnet sample, an offline command and six regression tests. Copy its
folder into any workspace; no packages, network or cave records are needed for
validation. Capturing fresh evidence uses only public read RPC methods.

[Payment evidence bridge](payment-evidence/README.md) connects all four lines:
bounded RPC reads, structural contracts, settlement/net ZTO or IMD payment
verification, and offline typed-data commitments. It binds replay to an independently
supplied policy and includes real historical and fresh mainnet observations,
vendored standard-library code and 14 integration tests. Copy its folder to use it
without the cave or line folders.

Gathering 03 adds [payment commitment explanation](payment-evidence/explain.py):
replay the checked payment, inspect its EIP-712 field words and compare an exact
client request, locating mismatches by JSON Pointer. The trace is vendored from
Line 4 and connects to the existing four-line bridge. Twelve integration tests
and a fresh real ZTO payment exercise it entirely offline after capture.

Gathering 04 adds payment domain binding: see `payment-evidence/bind.py` and its
README for a single offline decision requiring payment policy, exact client
encoding, and independently supplied domain/type to all match. No signing or
new coin is needed.

Gathering 05 adds `payment-evidence/corroborate.py`: two provider transcripts
must independently meet the payment policy and agree, then their complete
content commitment must match the separately reviewed intended request and
exact client encoding. It shares the current agreement and request comparison
pieces, with 16 integration tests and a detached offline trial. ZTO supplies the
real evidence; no additional coin, package or wallet is required.

Gathering 06 adds `payment-evidence/revisit.py`: preserve paired-provider policy
across a payment recheck, require both sampled heads to advance without alerts,
then bind the new evidence to an independently reviewed captured request and
compare the client's public account as well as EIP-712 encoding. Invalid policies
have exact document/contract rule pointers. Includes unchanged vendored line
pieces, 14 integration tests and a detached offline demo using real historical
ZTO observations. It never dispatches a captured method or promotes a baseline.

Gathering 07 adds `payment-evidence/time_review.py`: check an independently chosen
payment policy with exact UTF-8 source/rule locations, then replay timestamp-bearing
ZTO/IMD evidence against explicit caller time and age budgets. Includes real
historical ZTO fixtures and 13 integration tests. A detached folder reproduces
both acceptance and stale-evidence rejection offline. It reviews one observation
and does not substitute for the paired-provider requirements of `revisit.py`.

Gathering 08 adds `payment-evidence/paired_pinned_review.py`: require both saved
provider observations to satisfy the same payment and time policy, bind an exact
EIP-712 request to that complete pair, and compare a captured request against an
independently retained review pin. It vendors the latest paired-freshness and
review-pin pieces byte-for-byte. The historical ZTO demo and five integration
tests run offline; neither the demo's pin nor its self-compared request is an
independent approval or a real signing capture.

Gathering 09 adds `payment-evidence/checkpoint_review.py`: recheck both providers
against an independently retained baseline, require timely consistent progress,
then bind the exact current pair to a pinned request and explain changed client
values. Two byte-for-byte vendor copies, real historical ZTO inputs, 12 integration
tests and a detached offline trial are included. See the payment bridge README
for the command and the two different retained-pin schemes.

Gathering 10 adds `payment-evidence/anchored_payment.py`: it joins the bounded
parent-link walk to the structural payment policy and full EIP-712 evidence
commitment. The README includes a real historical ZTO demo and 14 regression tests.

Gathering 11 adds [exact payment precision review](payment-evidence/README.md#gathering-11-exact-payment-precision-review):
Line 4's integer analysis joined to the historical ZTO payment/domain gates.
The unchanged integer reviewer is vendored as an ordinary source file; the whole
payment-evidence folder remains portable and works offline. Matching EIP-712
encoding alone cannot hide an unsafe JSON integer representation from this review.

Gathering 12 adds [independent payment byte review](payment-evidence/README.md#gathering-12-independent-payment-byte-review):
Line 4's exact byte-field expectations now join the historical payment, domain,
full digest and integer-precision gates. Two byte fields must match separately
retained expectations; partial coverage or null expectations reject. The complete
folder is portable offline, with an unchanged vendor copy and 16 integration tests.

Gathering 13 adds [complete payment schema review](payment-evidence/SCHEMA.md),
joining Line 4's declaration comparison with Line 3's historical payment replay
and Line 2's contracts. Unused client declarations now reject even with the same
digest, exact bytes and accepted payment evidence.

Gathering 14 adds the [retained plan and settlement gate](settlement-gate/README.md).
Line 2's structural diagnostics join Line 3's non-weakening plan review and pinned
batch replay. Compatible plans cannot bypass evidence checks; weaker plans never
open evidence. Includes real historical ZTO fixtures, unchanged vendor copies,
14 tests and a detached offline trial.

Gathering 15 adds [ordered settlement review](ordered-settlement/README.md).
Line 2's structural diagnostics join Line 3's exact pinned order-plan replay.
Two settled transactions in the wrong required order now reject. Includes
unchanged ordinary vendor files, real historical ZTO evidence, 15 tests and
a detached offline trial. No plan hash is automatically updated.
