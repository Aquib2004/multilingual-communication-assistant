# Verification fixtures

These fixtures drive the automated tests and demonstrate what the verification
engine must catch. All content is fictional and de-identified.

## Expected results

| File | Case | Expected outcome |
| --- | --- | --- |
| `date_mismatch.json` | Source `September 8`, translation `9 de septiembre` | `FAIL` on the date |
| `time_mismatch.json` | Source `8:30 a.m.`, translation `8:00 a. m.` | `FAIL` on the time |
| `date_and_time_mismatch.json` | Both wrong in the same message | Two independent `FAIL`s |
| `ambiguous_deadline.json` | "Return the form soon" | `REVIEW_REQUIRED` — no usable deadline |
| `conditional_preserved.json` | "If you would like" stays optional | `PASS` |
| `conditional_broken.json` | Optional turned into a requirement | `FAIL` on the condition |
| `high_risk_suspension.json` | Suspension + appeal rights | `ESCALATED`, `HIGH` |
| `pii_placeholders.json` | Placeholder-only identifiers | No PII findings |

## Why the fixtures matter

Each of these is a failure mode that a fluent-looking translation can hide. They
exist so the checks are pinned by tests rather than by hope. See
[`../../docs/verification.md`](../../docs/verification.md) for the rule set.

The mismatch fixtures deliberately contain **wrong** dates and times. They are
test data, not messages to send.
