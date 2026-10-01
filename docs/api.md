# API Reference

Base URL: `http://localhost:8000/api`
Interactive documentation: `/docs` (Swagger UI) and `/redoc` (ReDoc).

All request and response bodies are JSON and validated with Pydantic v2.

## Conventions

### Error envelope

Every non-2xx response uses the same shape:

```json
{
  "error": {
    "code": "SOURCE_NOT_APPROVED",
    "message": "The source message must be approved before translation."
  },
  "request_id": "3f2b1c9e-..."
}
```

Stack traces and provider internals are **never** returned. They are logged
server-side against the same `request_id`.

### Error codes

| Code | HTTP | Meaning |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Request body failed schema validation |
| `MESSAGE_NOT_FOUND` | 404 | Unknown message id |
| `TRANSLATION_NOT_FOUND` | 404 | Unknown translation id |
| `SOURCE_NOT_APPROVED` | 409 | Approval gate: revise + approve first |
| `INVALID_STATE_TRANSITION` | 409 | Not allowed in the current state |
| `UNSUPPORTED_LANGUAGE` | 400 | Language/locale not registered |
| `MINIMUM_TWO_LANGUAGES` | 400 | Fewer than two target languages requested |
| `AI_PROVIDER_ERROR` | 502 | Upstream model/provider failure |
| `AI_PROVIDER_AUTH_ERROR` | 502 | Missing or invalid API key |
| `AI_PROVIDER_RATE_LIMIT` | 429 | Upstream rate limit |
| `AI_PROVIDER_TIMEOUT` | 504 | Upstream timeout |
| `AI_INVALID_OUTPUT` | 502 | Model output failed schema validation |
| `DATABASE_ERROR` | 503 | Database unavailable |

## Health & reference data

### `GET /api/health`

```json
{
  "status": "ok",
  "app": "multilingual-communication-assistant",
  "version": "0.1.0",
  "environment": "development",
  "ai_provider": "mock",
  "database": "connected",
  "timestamp": "2026-01-01T12:00:00Z"
}
```

`status` is `ok` or `degraded`.

### `GET /api/languages`

```json
{
  "source": { "code": "en", "name": "English", "script": "Latin", "direction": "ltr" },
  "targets": [
    { "code": "es", "name": "Spanish", "script": "Latin", "direction": "ltr",
      "reading_level_hint": "Aim for a grade 6-8 reading level.", "term_support": "full" },
    { "code": "hi", "name": "Hindi", "script": "Devanagari", "direction": "ltr", "term_support": "full" },
    { "code": "ur", "name": "Urdu", "script": "Arabic", "direction": "rtl", "term_support": "partial" }
  ]
}
```


### `GET /api/risk-levels`

Returns each level with `examples` and `review_requirements`.

## Messages (the Communication Workspace)

### `POST /api/messages`

Create a workspace. This is step **B** (Begin with purpose) plus the source.

```json
{
  "source_message": "Students are expected to return the form in a timely manner.",
  "audience": "families",
  "purpose": "Collect field trip permission forms",
  "action": "Return the signed permission form",
  "deadline": "Friday, September 18",
  "tone": "warm, respectful, direct",
  "risk_level": "routine",
  "target_languages": ["es", "hi"],
  "locale": "es-US",
  "protected_items": [
    { "item_type": "deadline", "value": "September 18", "must_match_exactly": true }
  ]
}
```

`201 Created` → `MessageResponse` with `state: "DRAFT"` and an `id`.
`422` if the source is empty or exceeds 5 000 characters.

### `GET /api/messages`

Query: `limit` (1–100, default 20), `offset`, `state`, `risk_level`.
Returns `{"items": [...], "total": n}`.

### `GET /api/messages/{id}`

Full workspace: source, revision, change summary, approval record, protected
items, translations, and the latest verification report. **404**
`MESSAGE_NOT_FOUND`.

### `POST /api/messages/rewrite`

Runs the plain-language engine. Either standalone (`{"source_message": "..."}`)
or against an existing message (`{"message_id": "..."}`).

```json
{
  "rewritten_message": "Please return the signed permission form by Friday, September 18.",
  "changes": [
    {
      "original": "Students are expected to return the form in a timely manner.",
      "revised": "Please return the signed permission form by Friday, September 18.",
      "reason": "Named the actor, replaced 'in a timely manner' with a usable deadline, and used a direct verb."
    }
  ],
  "open_questions": ["Confirm the exact delivery method for returning the form."],
  "reading_level": { "avg_sentence_length": 11.2, "passive_voice_detected": false },
  "state": "REVISED"
}
```

This step never changes meaning. It may only surface questions.

### `POST /api/messages/{id}/approve`

The **approval gate**.

```json
{ "approved": true, "reviewer": "initials only, optional", "notes": "Optional" }
```

- `approved: true` → state `APPROVED`, `approved_at` set, `approved_message`
  frozen as the translation source.
- `approved: false` → requires `notes`; state returns to `DRAFT` with feedback.

**409** `INVALID_STATE_TRANSITION` if already approved or no revision exists.

### `POST /api/messages/{id}/reject`

`{"notes": "Use the family-facing term 'family night' instead."}` → state
`DRAFT` with the feedback retained for the next rewrite.

### `GET /api/messages/{id}/protected-items`

Extracted fact-map candidates with `item_type`, `value`, `placeholder`,
`must_match_exactly`, and offsets.

### `DELETE /api/messages/{id}`

Deletes the workspace and its translations, reports, and protected items.
`204 No Content`. This is the privacy deletion path.

## Translations

### `POST /api/translations`

**Requires an approved message.** At least two target languages.

```json
{
  "message_id": "3f2b1c9e-...",
  "target_languages": ["es", "hi", "ur"],
  "locale": "es-US",
  "tone": "warm, respectful, direct",
  "reading_level": "grade 6"
}
```

Response contains a `translations` array; each entry has `id`,
`message_id`, `target_language`, `locale`, `translated_message`,
`protected_items`, `uncertainties`, `provider`, `model`, `created_at`.

**409** `SOURCE_NOT_APPROVED` — the gate. A translation is never produced from
an unapproved source.
**400** `MINIMUM_TWO_LANGUAGES`, `UNSUPPORTED_LANGUAGE`.
**502** `AI_PROVIDER_ERROR` / `AI_INVALID_OUTPUT`.
**429** `AI_PROVIDER_RATE_LIMIT`, **504** `AI_PROVIDER_TIMEOUT`.

### `GET /api/translations/{id}`

Single translation record. **404** `TRANSLATION_NOT_FOUND`.

## Verification

### `POST /api/verification`

`{"translation_id": "b91a..."}` → a `VerificationReport` with
`overall_status`, `summary`, `checks`, `back_translation`, `tone_assessment`,
`issues`, `risk`, `escalation_note`, `review_requirements`, `provider`, `model`.

`overall_status` ∈ `PASS | WARNING | REVIEW | FAIL | ESCALATED` and equals the
worst individual check status.

### `GET /api/verification/{id}`

Persisted report. **404** when absent.

## Escalation

### `POST /api/escalation/check`

```json
{ "text": "Your student has been suspended for three days. You may appeal.",
  "declared_risk_level": null }
```

```json
{
  "level": "HIGH",
  "declared_by_user": null,
  "evidence": [
    { "category": "discipline", "matched": ["suspended"], "excerpt": "has been suspended" },
    { "category": "legal_rights", "matched": ["appeal"], "excerpt": "You may appeal" }
  ],
  "escalation_note": "Professional human translation or interpretation is recommended for this high-consequence message.",
  "review_requirements": [
    "Use the organisation's approved professional translation or interpretation process.",
    "Do not rely on AI output alone for this content.",
    "Confirm rights language with the responsible office."
  ],
  "ai_output_is_final": false
}
```

`declared_risk_level` acts as a **floor** — a message declared `ROUTINE` that
triggers high-consequence signals still returns `HIGH`.

## Examples (demo mode)

### `GET /api/examples`

Bundled fictional, de-identified demo messages (`routine/`, `moderate-risk/`,
`verification/`) with risk level and suggested target languages. No real names,
phone numbers, or student IDs exist anywhere in the repository.

## Rate limiting

Not enabled by default. When deployed behind a reverse proxy, apply limits at
the edge. The API surfaces upstream provider rate limits as
`429 AI_PROVIDER_RATE_LIMIT` with `Retry-After`.
