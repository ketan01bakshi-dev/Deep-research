# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main`  | Yes       |

## Reporting a vulnerability

If you discover a security issue, **do not** open a public GitHub issue.

Email the maintainer (replace with your contact) or use GitHub **Private vulnerability reporting** if enabled on the repo.

Include:

- Description of the issue
- Steps to reproduce
- Impact assessment
- Suggested fix (optional)

## Secrets and credentials

- **Never** commit `.env`, API keys, or session folders under `docs/Research/`.
- Use `.env.example` as a template only.
- For hosted demos, store secrets in Streamlit Cloud **Secrets**, not in the repository.

## Public demo considerations

When running `PUBLIC_DEMO=true`:

- Use a dedicated `CURSOR_API_KEY` with spend alerts.
- Set `DEMO_PASSWORD` to limit casual access.
- Review `MAX_DEMO_MISSIONS_PER_DAY` regularly.

## Third-party services

This project sends prompts and tool data to:

- [Cursor](https://cursor.com/) (via `cursor-sdk`, proprietary)
- [Tavily](https://tavily.com/) (optional web search)

Users are responsible for complying with those providers' terms.
