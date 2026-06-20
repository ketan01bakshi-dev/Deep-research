# Contributing to Deep Research

Thank you for your interest in improving Deep Research.

## Development setup

```powershell
git clone https://github.com/YOUR_USERNAME/deep-research.git
cd deep-research
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
# Add CURSOR_API_KEY and TAVILY_API_KEY to .env
```

## Running tests

```powershell
.\run_tests.cmd
```

Or:

```powershell
.\.venv\Scripts\python.exe -m pytest tests packages\cursor_agent_core\tests -v --tb=short
```

## Bug-fix workflow

1. Reproduce the issue.
2. Apply the smallest correct fix.
3. Add a regression test in `tests/`.
4. Ensure the full suite passes before opening a PR.

## Pull requests

- Keep changes focused — one bug or feature per PR when possible.
- Match existing code style and naming.
- Do not commit `.env`, API keys, or `docs/Research/` session data.
- Update `README.md` if you change setup, env vars, or public behavior.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Do not open public issues for credential leaks.

## Questions

Open a [GitHub Discussion](https://github.com/YOUR_USERNAME/deep-research/discussions) or Issue.
