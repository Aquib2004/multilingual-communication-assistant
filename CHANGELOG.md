# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open-source release of the Multilingual Communication Assistant.
- BRIDGE workflow: purpose, plain-language rewrite, protected-item identification,
  contextual drafting, meaning verification, escalation.
- FastAPI backend with layered architecture (api / services / ai / verification / models).
- Provider-agnostic AI layer (`mock`, `openai`, `local`) selected via `AI_PROVIDER`.
- Plain-language rewriting with an explicit, non-skippable human approval gate.
- Protected-item extraction and placeholder-preserving translation.
- Verification engine: fact map, back-translation, tone/terminology review.
- Risk classification (ROUTINE / MODERATE / HIGH) with mandatory escalation.
- React + TypeScript + Vite + Tailwind Communication Workspace UI.
- PostgreSQL via SQLAlchemy with a SQLite fallback for zero-setup local runs.
- Demo mode with fictional, de-identified example messages.
