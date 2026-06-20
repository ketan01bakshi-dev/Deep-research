# Streamlit Community Cloud deployment

Deploy a free public demo at [share.streamlit.io](https://share.streamlit.io).

## Prerequisites

- Public GitHub repository containing this project
- [Cursor API key](https://cursor.com/dashboard/integrations) (use a **dedicated demo key** with spend alerts)
- [Tavily API key](https://tavily.com/)

## Steps

1. **Push to GitHub** — ensure `packages/agent_core` and `packages/cursor_agent_core` are in the repo.

2. **Sign in** to [share.streamlit.io](https://share.streamlit.io) with GitHub.

3. **New app** → select your repo, branch `main`, main file path: `app.py`.

4. **Advanced settings** → Python 3.12.

5. **Secrets** (Settings → Secrets) — paste from [.streamlit/secrets.toml.example](../.streamlit/secrets.toml.example):

   ```toml
   CURSOR_API_KEY = "..."
   TAVILY_API_KEY = "..."
   PUBLIC_DEMO = "true"
   DEMO_PASSWORD = "your-shared-password"
   MAX_DEMO_MISSIONS_PER_DAY = "10"
   DEMO_SESSION_TTL_HOURS = "72"
   DEMO_ALLOWED_DELIVERABLES = "answer"
   DEMO_ALLOW_PIPELINE = "false"
   ```

6. **Deploy** — wait for the build to finish.

7. **Update README** — replace the Streamlit badge URL with your app URL.

8. **Share demo password** in README or LinkedIn pinned comment (not in secrets).

## Limitations on Streamlit Cloud

| Feature | Cloud support |
|---------|---------------|
| Quick query / full mission (answer) | Yes |
| Report / slides (python libs) | Usually yes |
| Mind map (Node + Puppeteer) | Often **no** — disable in demo |
| Persistent sessions across redeploys | Ephemeral — acceptable for demo |
| HTTP API on port 8765 | Not exposed — Streamlit only |

## Cost control

- Set `MAX_DEMO_MISSIONS_PER_DAY` to 10 or lower
- Restrict `DEMO_ALLOWED_DELIVERABLES` to `answer`
- Keep `DEMO_ALLOW_PIPELINE=false`
- Monitor Cursor dashboard daily during LinkedIn traffic

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Import error for `agent_core` | Confirm `packages/` is in repo and `requirements.txt` uses `-e packages/...` |
| Missing API key | Check Secrets tab; redeploy after saving |
| App sleeps on free tier | First visitor may wait ~30s — mention in LinkedIn post |
| Build fails on pytest in requirements | pytest in requirements is fine; Streamlit ignores it at runtime |

## Custom subdomain

Streamlit Cloud → App settings → Custom subdomain → `your-name-deep-research.streamlit.app`
