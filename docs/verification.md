# Verification

The verification engine is the point of this project. A translation that
*looks* fluent is not evidence of a translation that is *correct*.

## 1. What gets verified

`app/verification/fact_extractor.py` runs a deterministic pass over the
approved source and, when available, an AI-assisted pass. The union is the
**fact map**: the checklist of everything that must survive translation.

| Item type | Example | Match rule |
| --- | --- | --- |
| `date` | `October 3` | Same calendar date after parsing; order/punctuation may differ per locale |
| `time` | `6:00–7:00 p.m.` | Same clock time; 12h/24h form may differ, offset may not |
| `datetime` | `September 8 at 8:30 a.m.` | Both parts must match |
| `url` | `https://example.org/rsvp` | Exact string, case-insensitive host only |
| `email` | `families@example.org` | Exact |
| `phone` | `+1 555 0100` | Digits only; punctuation and spacing may differ |
| `number` | `18`, `45-minute` | Digit sequence preserved |
| `money` | `$12.50` | Digits preserved; currency symbol may be localised |
| `name` | `Family Curriculum Night` | Translated consistently or retained; always `REVIEW_REQUIRED` |
| `program` | `Reading Buddies` | Same as `name` |
| `deadline` | `by October 3` | Date present and attached to the same action |
| `action` | `RSVP using the link` | Present, requested form, same actor |
| `condition` | `if you would like` | Conditionality preserved (optional must not become required) |
| `contact` | `[PROGRAM COORDINATOR], [PHONE]` | Role and route preserved |

## 2. Statuses

| Status | Meaning | UI |
| --- | --- | --- |
| `PASS` | Fact present and equivalent. | green |
| `WARNING` | Present but non-identical, or a locale convention changed the surface form. | amber |
| `FAIL` | Missing or contradicted (wrong number, wrong date). | red |
| `REVIEW_REQUIRED` | Cannot be decided automatically — proper nouns, ambiguous dates, tone. | blue/amber |

`overall_status` is the **worst** status among its checks, with `ESCALATED`
reserved for `HIGH` risk. A `FAIL` or `REVIEW_REQUIRED` anywhere sets
`human_review_required = true`.

## 3. Worked example: date mismatch

```jsonc
// approved source
"Please bring the permission form on September 8 at 8:30 a.m."
// translation under test (deliberately wrong)
"Traiga el formulario el 9 de septiembre a las 8:00 a. m."
```

| Item | Source | Translation | Status | Why |
| --- | --- | --- | --- | --- |
| date | September 8 | 9 de septiembre | `FAIL` | day differs (8 ≠ 9) |
| time | 8:30 a.m. | 8:00 a. m. | `FAIL` | minutes differ (30 ≠ 00) |
| action | bring the permission form | Traiga el formulario | `WARNING` | verb correct; "permission" unmatched as a protected term |


## 4. Back-translation

For every `deadline`, `action`, `condition`, and `contact` item:

1. The **critical sentence** containing the item is isolated from the target
   translation.
2. It is translated back into English.
3. The result is normalised and compared to the approved English sentence with
   a similarity ratio plus explicit field checks.

Back-translation is where meaning loss shows up. "May attend" → "debe asistir"
translates back as "must attend" — fluent, confident, and wrong. That is a
`FAIL`, not a warning.

Back-translation uses the configured AI provider when one is available, and a
deterministic glossary path when running on the mock provider, so the check
runs in CI.

## 5. Tone and pragmatic review

Tone cannot be reliably decided by a script, so it is always surfaced for a
human:

- `tone` — welcoming / neutral / mechanical / patronising / alarming
- `cultural_awkwardness` — phrases that translate literally but read oddly
- `terminology_notes` — recurring terms whose chosen sense may be wrong locally
  (e.g. "conference" → a large convention instead of a family–teacher meeting)

These are informational. The system reports what it noticed and asks a fluent
reviewer to decide.

## 6. Risk tiers and required review

| Level | Triggers (examples) | Required review |
| --- | --- | --- |
| `ROUTINE` | welcome, reminder, newsletter, classroom update | AI draft + fact check + bilingual review when available |
| `MODERATE` | permission, schedule change, participation, pickup rules | Approved workflow + fluent reviewer; confirm the response path works |
| `HIGH` | safety, health, medication, legal rights, discipline, suspension, disability services, emergency, threat, abuse, custody | **Do not rely on AI alone.** Use the approved professional translation / interpretation process. |

For `HIGH` risk the API response carries:

```json
{
  "status": "ESCALATED",
  "human_review_required": true,
  "escalation_note": "Professional human translation or interpretation is recommended for this high-consequence message.",
  "review_requirements": [
    "Use the organisation's approved professional translation or interpretation process.",
    "Do not rely on AI output alone for this content.",
    "Confirm legal rights language with the responsible office.",
    "Provide an interpretation option in the response path."
  ]
}
```

A user-declared risk level is treated as a **floor**: declaring `ROUTINE` for a
suspension letter still yields `HIGH`.

## 7. False confidence

Three rules keep this honest:

1. **Never certify.** No response field contains the word "certified" or
   "guaranteed". The AI prompt forbids it explicitly.
2. **Unknown is a valid answer.** When a comparison cannot be made, the status
   is `REVIEW_REQUIRED`. It is never left blank and never guessed.
3. **Ambiguity blocks, not defaults.** A numeric date like `10/03/2026` in a
   locale whose day/month order is unknown is escalated rather than assumed.

## 8. Verification record

`VerificationReport` is persisted with: every check, every issue, the
back-translation pairs, the tone assessment, the risk level with its evidence,
the escalation note, the provider used, and the model version. It is the
"what we checked, what we revised, what still needs a human" artefact the
project is required to produce.
