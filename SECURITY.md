# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅        |

## Reporting a Vulnerability

**Please do not open a public GitHub Issue for security problems.**

Report vulnerabilities privately via GitHub's "Report a vulnerability" button
(Security → Advisories → New draft advisory), or by email to the maintainer
listed in the repository's `package.json`-equivalent metadata.

Please include:

- A description of the issue and its impact
- Steps to reproduce, or a proof of concept
- The affected version / commit
- Any suggested mitigation

You can expect an acknowledgement within 72 hours and a status update within
7 days. Please give the maintainers a reasonable window to release a fix
before public disclosure.

## Security Design Principles

This project is designed with the following safeguards:

1. **No secrets in source control.** All credentials come from environment
   variables. `.env` is git-ignored; only `.env.example` is committed.
2. **No PII in the repository.** Every bundled example uses fictional or
   de-identified data and placeholder tokens such as `[FAMILY NAME]`, `[PHONE]`.
3. **Structured logging that excludes content.** Request IDs, operation names,
   durations, and provider names are logged. Message bodies are **not** logged
   unless `LOG_MESSAGE_CONTENT=true` is explicitly set.
4. **PII screening.** Incoming text is screened for patterns that look like
   personal data; warnings are surfaced to the user.
5. **Restricted CORS.** Only origins listed in `CORS_ORIGINS` are allowed.
6. **Safe error responses.** Internal exceptions and stack traces are logged
   server-side and replaced with generic, user-safe messages in API responses.
7. **Parameterized database access.** SQLAlchemy is used exclusively; no string
   interpolation into SQL.
8. **No certification claims.** The software never asserts that a translation
   is certified or guaranteed accurate.

## Limitations You Should Understand

- The mock provider is **rule-based**, not a neural model. It exists so the
  pipeline can be exercised offline. Do not use it for real-world outreach.
- High-consequence content (safety, health, legal rights, discipline,
  disability services, emergencies) **must not** rely on this tool alone. Use
  your organization's approved professional translation or interpretation process.
- A reverse proxy with TLS termination, rate limiting, and authentication
  **must** be placed in front of the API before it is exposed publicly. The
  reference application ships without user authentication by design.
