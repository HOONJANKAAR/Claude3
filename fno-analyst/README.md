# fno-analyst

Indian stocks, futures & options (F&O) CSV data analyst, built with the
[Mistral Agents SDK](https://docs.mistral.ai/studio/agents/overview) and deployed
as a Mistral-managed agent.

You share a Google Drive link to a CSV file and ask questions in plain language.
The agent fetches the file through your Google Drive connector and answers with
real numbers from your data. It has a fixed tool set and **no code execution**:

| Tool | Purpose |
| --- | --- |
| `register_csv` | Register CSV content fetched from Drive (name, row count, columns, preview) |
| `describe_columns` | Per-column type, nulls, unique count, numeric stats / top values |
| `preview_rows` | Raw row previews from an offset |
| `filter_rows` | Structured row filters (eq, gt, contains, in, between, ...) |
| `groupby_aggregate` | Group-by with count/sum/mean/median/min/max/std/nunique |

Sessions are stored by Mistral, so follow-up questions in the same conversation
remember the dataset and everything discussed earlier.

## Local development

```bash
uv sync
uv run python test_tools.py   # tool unit tests, no API key needed
uv run --env-file .env agents chat   # chat locally (needs MISTRAL_API_KEY in .env)
```

## Deploy (Mistral-managed)

```bash
git push
uv run --env-file .env agents deploy
uv run --env-file .env agents chat fno-analyst
```

The Google Drive connector (`google_drive_mcp`) must be connected by each user
in [Mistral Studio](https://console.mistral.ai/build/connectors) so the agent can
read their files on their behalf; the deployment is hardened for this.

## Call it from your own code

```python
import asyncio
from mistralai import agents

async def main() -> None:
    agent = agents.Agent.load_from(agent_name="fno-analyst")
    result = await agent.run("What's in my file <drive-link>?")
    print(result.text)

asyncio.run(main())
```
