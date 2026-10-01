# Contributing

Thank you for helping make family communication clearer and more inclusive.
This project is community-driven and every useful contribution is welcome —
code, documentation, translations, terminology, or bug reports.

## Code of Conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). By
contributing you agree to uphold it.

## Ways to Contribute

- **Report a bug** using the bug report issue template.
- **Suggest an enhancement** using the feature request issue template.
- **Improve the docs** — clarity issues are bugs too.
- **Add or correct a language entry** in `backend/app/core/languages.py`
  (locale, script, and reading-level guidance).
- **Improve the plain-language rules** in the mock provider so offline demos
  behave more like a real model.
- **Contribute terminology glossaries** per locale, so "conference", "office",
  or "field trip form" resolve to the locally understood sense.

## Getting Set Up

```bash
git clone https://github.com/Aquib2004/multilingual-communication-assistant.git
cd multilingual-communication-assistant

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env

# Frontend
cd ../frontend
npm install
```

Run `make help` for the full list of helper targets.

## Development Rules

1. **Small, focused changes.** One concern per module. No god classes, no god
   functions, no global mutable state.
2. **Type hints everywhere.** `mypy` must pass on `backend/app`.
3. **Tests are mandatory** for new behaviour. A change without a test will not
   be merged.
4. **Never hard-code secrets.** Use settings from `app/core/config.py`.
5. **Never add real personal data** — not in tests, fixtures, examples, or
   commit messages.
6. **Prompts belong in `app/ai/prompts/`**, not inline in service functions.
7. **AI output is never trusted.** Validate structured output with Pydantic and
   fail closed on malformed responses.

## Quality Gates

Run all of these before opening a pull request:

```bash
make lint        # ruff + eslint
make format      # black + prettier
make typecheck   # mypy + tsc
make test        # pytest + vitest
```

CI runs the same checks; they are not negotiable.

## Pull Requests

1. Branch from `main`: `git checkout -b feat/your-change`.
2. Make your change with tests.
3. Update `CHANGELOG.md` under `[Unreleased]`.
4. Update docs if behaviour or configuration changed.
5. Fill in the pull request template and link the related issue.

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add protected-item extraction for currency values
fix: flag time mismatch when locale uses 24-hour clock
test: cover missing-deadline ambiguity case
docs: explain back-translation thresholds
ci: run mypy on pull requests
```

## Reporting Security Issues

Do **not** open a public issue. Follow [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
