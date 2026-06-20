# Pre-launch checklist

Complete before publishing on LinkedIn.

## Repository

- [ ] Public GitHub repo created (`deep-research`)
- [ ] `LICENSE`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md` present
- [ ] `.env` and `docs/Research/` **not** in git
- [ ] `git log` reviewed — no leaked API keys
- [ ] Replace `YOUR_USERNAME` placeholders in README and CONTRIBUTING

## Local verification

- [ ] Fresh clone on clean machine (or new venv)
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `.\run_tests.cmd` — all tests pass
- [ ] `python scripts/verify_setup.py` — all checks pass
- [ ] `run_app.cmd` — mission completes with test keys

## Hosted demo (optional Tier 2)

- [ ] Deployed on Streamlit Community Cloud
- [ ] Secrets configured (see `.streamlit/secrets.toml.example`)
- [ ] Demo password works
- [ ] Daily mission cap enforced
- [ ] Cursor spend alert configured on demo key
- [ ] README badge URL updated

## Legal

- [ ] [docs/LEGAL.md](LEGAL.md) reviewed — contact email updated
- [ ] AI disclaimer visible in app footer
- [ ] Cursor SDK proprietary dependency noted in README

## Marketing

- [ ] 60–90s demo video recorded
- [ ] Hero screenshot saved
- [ ] LinkedIn post drafted ([LINKEDIN_LAUNCH.md](LINKEDIN_LAUNCH.md))
- [ ] GitHub Issues enabled for feedback
- [ ] Soft launch: 5 contacts tested clone + demo URL

## Post-launch (first 48 hours)

- [ ] Monitor Cursor + Tavily spend
- [ ] Respond to GitHub Issues / LinkedIn comments
- [ ] Pin setup instructions comment on LinkedIn post
