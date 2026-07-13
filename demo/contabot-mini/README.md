# ContaBot Mini — Auditable XML Review Demo

A small, runnable illustration of the workflow thinking behind the private ContaBot project.

It takes a **fake** Paraguay-style invoice XML through a bounded pipeline:

`parse → validate → route to review → append decision → export audit summary`

![Workflow diagram](../../assets/contabot-workflow.svg)

## What this proves

- Missing or ambiguous values become explicit reason codes; the program does not guess.
- Initial processing status stays unchanged after human review.
- Review decisions are appended to history.
- Review state and workflow state are derived separately.
- The export contains a source checksum and bounded audit summary, not raw XML.

## Run it

No packages or credentials are required—only Python 3.9 or newer.

```bash
cd demo/contabot-mini
python3 contabot_demo.py sample-data/sample-invoice.xml
python3 contabot_demo.py sample-data/sample-invoice.xml --decision approve
```

The fake invoice intentionally omits the receiver tax ID, producing:

```json
{
  "base_status": "needs_review",
  "reason_codes": ["missing_receiver_tax_id"],
  "review_state": "approved",
  "workflow_state": "review_approved",
  "decision_count": 1
}
```

The real command prints additional non-sensitive invoice summary fields and the source SHA-256.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

The test suite checks parsing, review routing, immutable base status, append-only decisions, invalid actions, and bounded export behavior.

## Scope and limitations

This is a public-safe educational demo built from fake data. It is not a copy of the private application, does not implement SIFEN submission, and must not be used for tax or compliance decisions. Its purpose is to make the workflow invariants visible and runnable.
