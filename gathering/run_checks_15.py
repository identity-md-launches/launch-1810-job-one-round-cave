#!/usr/bin/env python3
"""Run every line's documented offline check without modifying line folders."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def main():
    if Path.cwd().resolve() != ROOT:
        raise SystemExit('Run this command from the repository root')
    scratch = ROOT / 'test/scratch'
    scratch.mkdir(parents=True, exist_ok=True)
    # Line 4's tests create/remove fixtures beside their source. Run an exact
    # copy in scratch so even temporary line-folder modifications are avoided.
    shutil.copytree(ROOT / 'line-4/tools/typed-digest', scratch / 'typed-digest', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'line-4/tools/review-changes', scratch / 'review-changes', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'line-4/tools/array-review', scratch / 'array-review', dirs_exist_ok=True)
    commands = [
        ['line-1/tools/rpc_snapshot.py', '--verify', 'line-1/tools/bounded-rpc-snapshot/sample-zto-supply.json'],
        ['line-1/tools/bounded-rpc-snapshot/snapshot.py', '--verify', 'line-1/tools/bounded-rpc-snapshot/sample-zto-supply.json'],
        ['line-1/tools/anchored-zto-snapshot/anchored.py', '--verify', 'line-1/tools/anchored-zto-snapshot/sample.json'],
        ['line-2/tools/json-contract/check.py', 'line-2/tools/json-contract/report.contract.json', 'line-2/tools/json-contract/report.example.json'],
        ['line-2/tools/json-contract/test_check.py'],
        ['line-2/tools/ordered-deliverables/check.py', 'line-2/tools/ordered-deliverables/handoff.contract.json', 'line-2/tools/ordered-deliverables/handoff.example.json'],
        ['line-2/tools/ordered-deliverables/test_ordered.py'],
        ['line-2/tools/batch-contract/check.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/01.json', 'dist/line-2/22.json', 'dist/line-2/23.json'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/settlement-check', '-p', 'test_*.py', '-v'],
        ['line-3/tools/payment-witness/witness.py', '--replay', 'line-3/tools/payment-witness/live-evidence.json'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/payment-witness', '-p', 'test_*.py', '-v'],
        ['gathering/offline_boundary.py'],
        ['line-4/tools/typed-digest/typed_digest.py', 'line-4/tools/typed-digest/zto-example.json', '--expect', '0xc292388738e2cf2c7f57b9b8926821aff508ed38c1b355020cc7dc459dbbb8cb'],
        ['-m', 'unittest', 'discover', '-s', 'test/scratch/typed-digest', '-p', 'test_*.py', '-v'],
        ['line-4/tools/typed-trace/typed_trace.py', 'line-4/tools/typed-trace/zto-payment.json', '--expect', '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774', '--summary'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/typed-trace', '-p', 'test_*.py', '-v'],
        ['shared/rpc-evidence/test_bridge.py'],
        ['shared/rpc-evidence/verify.py', 'shared/rpc-evidence/chain-id.snapshot.json'],
        ['shared/payment-evidence/test_evidence.py'],
        ['shared/payment-evidence/explain.py', 'shared/payment-evidence/example.transcript.json', 'shared/payment-evidence/example.policy.json', '--summary'],
        ['shared/payment-evidence/test_explain.py'],
        ['line-1/tools/safe-snapshot-files/test_safe_files.py'],
        ['line-1/tools/anchored-zto-snapshot/anchored.py', '--verify', 'line-1/tools/safe-snapshot-files/live-zto.json'],
        ['line-1/tools/safe-snapshot-files/safe_files.py', 'line-1/tools/safe-snapshot-files/live-zto.json'],
        ['line-2/tools/bounded-contract/check.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/01.json', 'dist/line-2/22.json', 'dist/line-2/23.json', 'dist/line-2/24.json'],
        ['line-2/tools/bounded-contract/test_check.py'],
        ['line-3/tools/discovery-diagnostic/diagnose.py', '--replay-known'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/discovery-diagnostic', '-p', 'test_*.py'],
        ['line-4/tools/domain-check/domain_check.py', 'line-4/tools/domain-check/zto-payment.json', '--chain-id', '1', '--name', 'Read-only Payment Evidence', '--version', '1', '--primary-type', 'PaymentEvidence', '--no-verifier', '--expect', '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/domain-check', '-v'],
        ['shared/payment-evidence/test_bind.py'],
        ['shared/payment-evidence/bind.py', 'shared/payment-evidence/example.transcript.json', 'shared/payment-evidence/example.policy.json', 'shared/payment-evidence/example.typed-data.json', '--chain-id', '1', '--name', 'Read-only Payment Evidence', '--version', '1', '--primary-type', 'PaymentEvidence', '--no-verifier', '--summary']]
    commands.extend([
        ['line-1/tools/hash-pinned-zto/pinned.py', '--verify', 'line-1/tools/hash-pinned-zto/live-zto.json'],
        ['line-1/tools/hash-pinned-zto/test_pinned.py'],
        ['line-2/tools/repair-review/review.py', 'line-2/tools/repair-review/handoff.contract.json', 'line-2/tools/repair-review/before.example.json', 'line-2/tools/repair-review/after.example.json'],
        ['line-2/tools/repair-review/test_review.py'],
        ['line-2/tools/bounded-contract/check.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/25.json'],
        ['line-3/tools/provider-agreement/agreement.py', '--demo'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/provider-agreement', '-p', 'test_*.py', '-v'],
        ['line-4/tools/request-compare/request_compare.py', 'line-4/tools/request-compare/zto-intended.json', 'line-4/tools/request-compare/zto-intended.json', '--summary'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/request-compare', '-v'],
    ])
    commands.extend([
        ['shared/payment-evidence/test_corroborate.py'],
        ['shared/payment-evidence/corroborate.py', 'shared/payment-evidence/example.paired.json', 'shared/payment-evidence/example.paired-policy.json', 'shared/payment-evidence/example.paired-intended.json', 'shared/payment-evidence/example.paired-intended.json', '--summary'],
    ])
    commands.extend([
        ['line-1/tools/compare-zto-snapshots/compare.py', 'line-1/tools/hash-pinned-zto/live-zto.json', 'line-1/tools/compare-zto-snapshots/live-zto.json'],
        ['line-1/tools/compare-zto-snapshots/test_compare.py'],
        ['line-2/tools/rule-locator/explain.py', 'shared/payment-evidence/policy.contract.json', 'shared/payment-evidence/example.policy.json'],
        ['line-2/tools/rule-locator/test_explain.py'],
        ['line-2/tools/bounded-contract/check.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/26.json'],
        ['line-3/tools/payment-recheck/recheck.py', '--demo'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/payment-recheck', '-v'],
        ['line-4/tools/rpc-request-check/rpc_request_check.py', 'line-4/tools/rpc-request-check/zto-envelope.json', 'line-4/tools/rpc-request-check/zto-envelope.json', '--summary'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/rpc-request-check', '-v'],
    ])
    commands.extend([
        ['shared/payment-evidence/test_revisit.py'],
        ['shared/payment-evidence/revisit.py', 'shared/payment-evidence/example.paired.json', 'shared/payment-evidence/round05.paired.json', 'shared/payment-evidence/example.paired-policy.json', 'shared/payment-evidence/example.revisit-envelope.json', 'shared/payment-evidence/example.revisit-envelope.json', '--summary'],
    ])
    commands.extend([
        ['line-1/tools/snapshot-report/report.py', 'line-1/tools/compare-zto-snapshots/live-zto.json'],
        ['line-1/tools/snapshot-report/test_report.py'],
        ['line-2/tools/source-locator/locate.py', 'shared/payment-evidence/policy.contract.json', 'shared/payment-evidence/example.policy.json'],
        ['line-2/tools/source-locator/test_locate.py'],
        ['line-2/tools/bounded-contract/check.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/27.json'],
        ['line-3/tools/settlement-freshness/freshness.py', '--demo'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/settlement-freshness', '-v'],
        ['line-4/tools/request-set-check/request_set_check.py', 'line-4/tools/request-set-check/zto-set.json', 'line-4/tools/request-set-check/zto-set.json', '--summary'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/request-set-check', '-v'],
    ])
    commands.extend([
        ['shared/payment-evidence/test_time_review.py'],
        ['shared/payment-evidence/time_review.py', 'shared/payment-evidence/example.timed-transcript.json', 'shared/payment-evidence/example.timed-policy.json', '--as-of', '1792008919', '--max-head-age', '120', '--max-finalized-age', '1200', '--future-skew', '30'],
    ])
    commands.extend([
        ['line-1/tools/revisit-zto-snapshot/revisit.py', '--verify', 'line-1/tools/compare-zto-snapshots/live-zto.json', 'line-1/tools/revisit-zto-snapshot/live-revisit.json'],
        ['line-1/tools/revisit-zto-snapshot/test_revisit.py'],
        ['line-2/tools/bounded-contract/check.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/28.json'],
        ['line-2/tools/contract-change/review.py', 'line-2/tools/json-contract/record.contract.json', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/26.json', 'dist/line-2/27.json'],
        ['line-2/tools/contract-change/test_review.py'],
        ['line-3/tools/paired-freshness/paired.py', '--demo'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/paired-freshness', '-p', 'test_*.py', '-v'],
        ['line-4/tools/review-pin/review_pin.py', 'check', 'line-4/tools/review-pin/zto-set.json', 'line-4/tools/review-pin/zto-set.json', '--expect', 'c1f7a3ff0b7cf878d16be782f567b2bf89f88e9b962ed64210eeaeb2cf6d7023'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/review-pin', '-v'],
    ])
    commands.extend([
        ['shared/payment-evidence/test_paired_pinned_review.py'],
        ['shared/payment-evidence/paired_pinned_review.py', 'shared/payment-evidence/paired-pinned-evidence.json', 'shared/payment-evidence/paired-pinned-policy.json', 'shared/payment-evidence/paired-pinned-intended.json', 'shared/payment-evidence/paired-pinned-intended.json', '--expect-pin', '8122b8ba057657d449c42e1c0c857be88eda97aebb8c836b07b2cf3589e8316e', '--as-of', '1792012453', '--max-head-age', '120', '--max-finalized-age', '1200', '--future-skew', '60'],
    ])
    commands.extend([
        ['line-1/tools/batched-zto-snapshot/batch.py', '--verify', 'line-1/tools/batched-zto-snapshot/live-batch.json'],
        ['line-2/tools/batch-source/locate.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/27.json', 'dist/line-2/28.json'],
        ['line-2/tools/batch-source/test_locate.py'],
        ['line-2/tools/bounded-contract/check.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/29.json'],
        ['line-3/tools/paired-recheck/recheck_pair.py', '--demo'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/paired-recheck', '-v'],
        ['line-4/tools/review-changes/review_changes.py', 'line-4/tools/review-changes/zto-set.json', 'line-4/tools/review-changes/zto-set.json', '--expect', 'c1f7a3ff0b7cf878d16be782f567b2bf89f88e9b962ed64210eeaeb2cf6d7023'],
        ['-m', 'unittest', 'discover', '-s', 'test/scratch/review-changes', '-v'],
    ])
    commands.extend([
        ['line-1/tools/batched-zto-snapshot/batch.py', '--verify', 'gathering/live-batch-09.json'],
        ['shared/payment-evidence/test_checkpoint_review.py'],
        ['shared/payment-evidence/checkpoint_review.py', 'shared/payment-evidence/checkpoint-baseline.json', 'shared/payment-evidence/paired-pinned-evidence.json', 'shared/payment-evidence/paired-pinned-policy.json', 'shared/payment-evidence/paired-pinned-intended.json', 'shared/payment-evidence/paired-pinned-intended.json', '--baseline-pin', 'dd94a4fb3ef241db9cffbf8ccb24b4486e0eea308b1c34a7e0668f6c92f90dd4', '--request-pin', '8122b8ba057657d449c42e1c0c857be88eda97aebb8c836b07b2cf3589e8316e', '--as-of', '1792012453', '--max-head-age', '120', '--max-finalized-age', '1200', '--future-skew', '60'],
    ])
    commands.extend([
        ['line-1/tools/two-source-zto/agreement.py', '--verify', 'line-1/tools/two-source-zto/live-agreement.json'],
        ['line-2/tools/source-guard/review.py', 'line-2/tools/source-locator/invalid-report.result.json', 'line-2/tools/json-contract/report.contract.json', 'line-2/tools/rule-locator/report.invalid.json'],
        ['line-2/tools/source-guard/test_review.py'],
        ['line-3/tools/anchor-bridge/bridge.py', '--demo'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/anchor-bridge', '-v'],
        ['line-4/tools/string-review/string_review.py', 'line-4/tools/string-review/zto-payment.json', '--expect', '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/string-review', '-v'],
    ])
    commands.extend([
        ['line-1/tools/retained-snapshot-pin/pin.py', 'line-1/tools/two-source-zto/live-agreement.json', '--expected-sha256', 'bb1ce8c232f7d62e83341d3da502a340ce2f8da12cf84580bcc537a3bf3ccb19'],
        ['line-1/tools/retained-snapshot-pin/test_pin.py'],
        ['line-2/tools/batch-guard/review.py', 'line-2/tools/batch-guard/records.report.json', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/29.json', 'dist/line-2/30.json'],
        ['line-2/tools/batch-guard/test_review.py'],
        ['line-2/tools/bounded-contract/check.py', 'line-2/tools/ordered-deliverables/record.strict.contract.json', 'dist/line-2/30.json', 'dist/line-2/31.json'],
        ['line-3/tools/tx-position/position.py', '--demo'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/tx-position', '-v'],
        ['line-4/tools/integer-review/integer_review.py', 'line-4/tools/integer-review/zto-payment.json', '--expect', '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/integer-review', '-v'],
        ['shared/payment-evidence/test_anchored_payment.py'],
    ])
    commands.extend([
        ['line-1/tools/generic-snapshot-diff/diff.py', 'line-1/tools/bounded-rpc-snapshot/sample-zto-supply.json', 'line-1/tools/generic-snapshot-diff/live-zto-supply.json'],
        ['line-2/tools/source-context/show.py', 'shared/payment-evidence/policy.contract.json', 'shared/payment-evidence/example.policy.json'],
        ['line-2/tools/source-context/test_show.py'],
        ['line-3/tools/pinned-position/pinned.py', '--demo'],
        ['-m', 'unittest', 'discover', '-s', 'line-3/tools/pinned-position', '-v'],
        ['line-4/tools/bytes-review/bytes_review.py', 'line-4/tools/bytes-review/zto-payment.json', '--bytes-expect', 'line-4/tools/bytes-review/zto-bytes.json', '--digest-expect', '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774'],
        ['-m', 'unittest', 'discover', '-s', 'line-4/tools/bytes-review', '-v'],
        ['shared/payment-evidence/test_precision_payment.py'],
    ])
    commands.extend([
        ['line-1/tools/batch-response-review/review.py', 'line-1/tools/batch-response-review/zto-batch.json'],
        ['-m','unittest','discover','-s','line-1/tools/batch-response-review','-v'],
        ['line-2/tools/html-review/review.py','shared/payment-evidence/policy.contract.json','shared/payment-evidence/example.policy.json'],
        ['line-2/tools/html-review/test_review.py'],
        ['line-3/tools/settlement-batch/batch.py','--demo'],
        ['-m','unittest','discover','-s','line-3/tools/settlement-batch','-v'],
        ['line-4/tools/schema-review/schema_review.py','line-4/tools/schema-review/zto-payment.json','--schema-expect','line-4/tools/schema-review/zto-schema.json','--digest-expect','0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774'],
        ['-m','unittest','discover','-s','line-4/tools/schema-review','-v'],
        ['shared/payment-evidence/test_byte_payment.py'],
    ])
    commands.extend([
        ['line-1/tools/snapshot-select/select_result.py','line-1/tools/snapshot-select/live-block.json','--pointer','/transactions/0'],
        ['line-1/tools/snapshot-select/select_result.py','line-1/tools/bounded-rpc-snapshot/sample-zto-supply.json'],
        ['-m','unittest','discover','-s','line-1/tools/snapshot-select','-v'],
        ['line-2/tools/sarif-review/review.py','shared/payment-evidence/policy.contract.json','shared/payment-evidence/example.policy.json'],
        ['line-2/tools/sarif-review/test_review.py'],
        ['line-3/tools/settlement-plan-diff/plan_diff.py','--demo'],
        ['-m','unittest','discover','-s','line-3/tools/settlement-plan-diff','-v'],
        ['line-4/tools/array-review/array_review.py','line-4/tools/array-review/zto-batch.json','--expect','line-4/tools/array-review/zto-arrays.json','--digest-expect','0xafd46e38940aa3cad45ccacf9ebbea5686570df15dcbf08e79119502d95605ba'],
        ['-m','unittest','discover','-s','test/scratch/array-review','-v'],
        ['shared/payment-evidence/test_schema_payment.py'],
    ])
    # New round tools; keep all source-writing suites in scratch copies.
    shutil.copytree(ROOT / 'line-4/tools/schema-review', scratch / 'schema-review', dirs_exist_ok=True)
    commands = [[a.replace('line-4/tools/schema-review', 'test/scratch/schema-review') if a == 'line-4/tools/schema-review' else a for a in args] for args in commands]
    commands.extend([
        ['line-1/tools/snapshot-integer/decode.py','line-1/tools/snapshot-integer/live-zto.json','--encoding','uint256','--decimals','18'],
        ['line-1/tools/snapshot-integer/decode.py','line-1/tools/snapshot-select/live-block.json','--pointer','/number','--encoding','quantity'],
        ['-m','unittest','discover','-s','line-1/tools/snapshot-integer','-v'],
        ['line-2/tools/jsonl-contract/check.py','shared/payment-evidence/policy.contract.json','line-2/tools/jsonl-contract/zto-policy.jsonl'],
        ['line-2/tools/jsonl-contract/test_check.py'],
        ['line-3/tools/settlement-order/order.py','--demo'],
        ['-m','unittest','discover','-s','line-3/tools/settlement-order','-v'],
        ['line-4/tools/hash-witness/hash_witness.py','line-4/tools/hash-witness/zto-trace.json','--expect','0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774'],
        ['line-4/tools/hash-witness/hash_witness.py','line-4/tools/hash-witness/ether-mail-trace.json','--expect','0xbe609aee343fb3c4b28e1df9e632fca64fcfaede20f02e86244efddf30957bd2'],
        ['-m','unittest','discover','-s','line-4/tools/hash-witness','-v'],
        ['shared/settlement-gate/test_gate.py'],
    ])
    results = []
    for args in commands:
        command = [sys.executable, '-B', *args]
        started = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, timeout=45, env={'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin'})
        results.append({'command': ' '.join(['python3', '-B', *args]),
                        'exitCode': result.returncode, 'seconds': round(time.monotonic()-started, 3),
                        'stdout': result.stdout if len(result.stdout) < 15000 else '[large HTML output; SHA-256 ' + __import__('hashlib').sha256(result.stdout.encode()).hexdigest() + '; bytes ' + str(len(result.stdout.encode())) + ']', 'stderr': result.stderr})
        print('PASS' if result.returncode == 0 else 'FAIL', ' '.join(args), flush=True)
    for group in ['line-1', 'line-2', 'line-3', 'line-4', 'shared']:
        selected = [r for r in results if group in r['command'] or (group == 'line-4' and any(x in r['command'] for x in ('test/scratch/typed-digest', 'test/scratch/review-changes', 'test/scratch/array-review', 'test/scratch/schema-review'))) or (group == 'line-3' and 'gathering/offline_boundary.py' in r['command'])]
        (ROOT / ('gathering/check-15-' + group + '.json')).write_text(json.dumps(selected, separators=(',', ':'))+'\n')
    return 0 if all(r['exitCode'] == 0 for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
