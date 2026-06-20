# Deep Research HTTP API

Optional FastAPI layer for running missions without Streamlit.

## Run

```cmd
cd "D:\Agents\Deep research"
.\run_api.cmd
```

Base URL: `http://localhost:8765`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/missions` | Start async mission (`use_pipeline` optional) |
| GET | `/missions/{job_id}` | Poll job status |
| POST | `/sessions/{session_id}/follow-up` | Async follow-up on session |
| POST | `/sessions/{session_id}/corpus/query` | RAG-lite query over session corpus |
| GET | `/sessions/{session_id}` | Session metadata |
| GET | `/sessions/{session_id}/export` | ZIP as base64 (`enhanced=true` default) |

## Example

```bash
curl -X POST http://localhost:8765/missions -H "Content-Type: application/json" -d "{\"topic\":\"CRISPR in agriculture\",\"deliverables\":[\"answer\"]}"
```
