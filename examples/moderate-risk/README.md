# Demo examples — MODERATE risk

Moderate-consequence messages are instructions tied to participation, permissions,
or schedule changes. They require an approved workflow plus a fluent reviewer,
and the response path must be confirmed to work.

| File | Scenario | Risk |
| --- | --- | --- |
| `schedule_change.json` | Change to the school day start time | moderate |
| `participation_consent.json` | Consent for a photo/video recording | moderate |

All content is fictional and de-identified.

For these, the verification report should surface a `REVIEW_REQUIRED` on tone and
terminology even when every fact passes. That is the intended behaviour: a fluent
human still decides whether "consent" landed as a request or an obligation.
