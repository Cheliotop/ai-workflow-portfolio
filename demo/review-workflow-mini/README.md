# Review Workflow Mini — a runnable worked example

Most of my work lives in private client repositories. This is the part I can hand you and let you execute yourself.

It's a small, self-contained pipeline that takes a **fake** invoice XML through the shape of review I use whenever automation makes a decision a person is accountable for:

`parse → validate → route to review → append decision → export audit summary`

## Why this exists

Any system that decides things on a human's behalf eventually has to answer one question: *why is this record in the state it's in?*

If the answer requires guessing, reading logs, or asking the person who built it, the system has failed — no matter how well it parses. This demo makes the invariants that prevent that failure visible and executable.

## What it demonstrates

- Missing or ambiguous values become **explicit reason codes**. The program never guesses.
- The initial processing status is **immutable** — human review does not overwrite what the machine originally found.
- Review decisions are **appended** to history, never replaced. You can always reconstruct the sequence.
- Review state and workflow state are **derived separately**, so a disagreement between them is visible rather than silently resolved.
- The export carries a source checksum and a bounded summary — **not** the raw document.

## Run it

No packages, no credentials, no network. Python 3.9 or newer, standard library only.

```bash
cd demo/review-workflow-mini
python3 review_demo.py sample-data/sample-invoice.xml
python3 review_demo.py sample-data/sample-invoice.xml --decision approve
```

The sample invoice deliberately omits the receiver tax ID, so you can watch it route to review rather than pass silently:

```json
{
  "base_status": "needs_review",
  "reason_codes": ["missing_receiver_tax_id"],
  "review_state": "approved",
  "workflow_state": "review_approved",
  "decision_count": 1
}
```

Note that `base_status` stays `needs_review` even after approval. That is the point, not a bug: the machine's original finding survives the human's decision.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

Five tests cover parsing, review routing, immutable base status, append-only decisions, rejected invalid actions, and bounded export behavior. They run in CI on every push to this repository — the badge on the [main README](../../README.md) reflects their current state.

## Scope and limitations

This is a public-safe worked example built entirely from fake data. It is not extracted from any client system, implements no government submission of any kind, and must not be used for tax or compliance decisions.

Its only job is to make the workflow invariants visible, runnable, and arguable.
