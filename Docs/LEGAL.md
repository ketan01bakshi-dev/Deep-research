# Legal & Privacy

_Last updated: June 2026_

## AI disclaimer

Deep Research uses large language models and automated web search. **Outputs may be inaccurate, incomplete, or outdated.** Verify important facts against primary sources. This tool does not provide professional, medical, legal, or financial advice.

## Privacy

### What data is processed

When you run a mission, the application may:

- Send your prompts and tool outputs to **Cursor** (model inference via `cursor-sdk`)
- Send search queries to **Tavily** (if `TAVILY_API_KEY` is configured)
- Download PDFs and web pages from URLs discovered during research
- Store session artifacts locally under `docs/Research/{session_id}/` (papers, reports, logs)

### Hosted demo (Streamlit Cloud)

If you use a public demo instance operated by the project maintainer:

- Your research topics and outputs may be stored on the host's server temporarily
- Sessions may be deleted automatically after the demo retention period (default 72 hours)
- Do not submit confidential or personal data to a public demo

### Self-hosted

If you clone and run locally, data stays on your machine except for calls to Cursor and Tavily using **your** API keys.

## Terms of use (summary)

By using Deep Research you agree to:

- Use the tool lawfully and not to abuse API quotas or hosted demos
- Accept that beta software may change or break without notice
- Respect copyright on downloaded papers and third-party content
- Obtain your own API keys and comply with [Cursor](https://cursor.com/terms) and [Tavily](https://tavily.com/) terms

## Third-party dependencies

| Component | License / terms |
|-----------|-----------------|
| Deep Research (this repo) | MIT — see [LICENSE](../LICENSE) |
| `cursor-sdk` | Proprietary — requires Cursor account and API key |
| Tavily | Third-party API — subject to Tavily terms |

## Data deletion

**Self-hosted:** Delete folders under `docs/Research/` manually.

**Hosted demo:** Sessions expire automatically; contact the maintainer for urgent deletion requests.

## Contact

Replace with your email: `hello@example.com`

Open GitHub Issues for product feedback (not for sensitive data).
